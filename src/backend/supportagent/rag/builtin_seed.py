import hashlib
import os

from supportagent.core.models import Document
from supportagent.html_utils import html_to_text
from supportagent.seed_content import CONFLUENCE_PAGES, JIRA_ISSUES, PROJECTS

from .chunking import chunk_document
from .embeddings import embed_texts, get_embedding_client
from .vector_store import create_schema, get_connection, upsert_chunk


PROJECT_PRODUCT_LINES = {
    "hausrat": "household",
    "wohngebaeude": "residential_building",
    "kfz": "vehicle",
    "haftpflicht": "liability",
    "rechtsschutz": "legal_expense",
    "schadenbearbeitung": "all",
}


def stable_source_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def builtin_documents() -> list[Document]:
    documents: list[Document] = []
    for page in [*PROJECTS, *CONFLUENCE_PAGES]:
        title = page["title"]
        documents.append(
            Document(
                text=f"{title}\n\n{html_to_text(page['body'])}",
                metadata={
                    "source": "confluence",
                    "source_id": stable_source_id("seed", title),
                    "title": title,
                    "space_id": "seed",
                    "labels": page.get("labels", []),
                    "version": 1,
                    "approval_status": "approved",
                    "document_type": "claims_guideline" if "claims" in page.get("labels", []) else "product_guideline",
                    "product_line": PROJECT_PRODUCT_LINES.get(page.get("project", ""), "all"),
                    "jurisdiction": "DE",
                    "effective_from": "2026-01-01",
                    "effective_to": None,
                    "owner_team": "Insurance Knowledge Management",
                    "updated_at": "2026-07-16",
                    "url": f"seed://insurance-kb/{stable_source_id('page', title)}",
                },
            )
        )

    for issue in JIRA_ISSUES:
        title = issue["summary"]
        parts = [title, issue.get("description", ""), *issue.get("comments", [])]
        documents.append(
            Document(
                text="\n\n".join(part for part in parts if part),
                metadata={
                    "source": "jira",
                    "source_id": stable_source_id("seed-jira", title),
                    "issue_key": stable_source_id("DEMO", title).upper(),
                    "title": title,
                    "project_key": "DEMO",
                    "issue_type": issue.get("issue_type", "Task"),
                    "status": "Seeded",
                    "approval_status": "unapproved",
                    "document_type": "documentation_issue",
                    "product_line": PROJECT_PRODUCT_LINES.get(issue.get("project", ""), "all"),
                    "jurisdiction": "DE",
                    "labels": issue.get("labels", []),
                    "updated_at": "2026-07-16",
                    "url": f"seed://insurance-jira/{stable_source_id('issue', title)}",
                },
            )
        )
    return documents


def ensure_rag_schema() -> None:
    dimensions = int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))
    conn = get_connection()
    try:
        create_schema(conn, dimensions)
    finally:
        conn.close()


def seed_builtin_rag(skip_if_exists: bool = True) -> tuple[int, int]:
    dimensions = int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))
    conn = get_connection()
    try:
        create_schema(conn, dimensions)
        existing_count = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
        if skip_if_exists and existing_count:
            return 0, existing_count

        chunks = [chunk for doc in builtin_documents() for chunk in chunk_document(doc)]
        embeddings = embed_texts(get_embedding_client(), [chunk["content"] for chunk in chunks])
        for chunk, embedding in zip(chunks, embeddings):
            upsert_chunk(conn, chunk, embedding)
        conn.commit()
        total_count = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
        return len(chunks), total_count
    finally:
        conn.close()


def seed_builtin_rag_if_enabled() -> None:
    enabled = os.environ.get("SEED_BUILTIN_RAG_ON_STARTUP", "false").lower() in {"1", "true", "yes"}
    if enabled:
        seed_builtin_rag(skip_if_exists=True)


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    stored_count, total_count = seed_builtin_rag(skip_if_exists=False)
    print(f"Stored {stored_count} built-in RAG chunks; total chunks now {total_count}")


if __name__ == "__main__":
    main()
