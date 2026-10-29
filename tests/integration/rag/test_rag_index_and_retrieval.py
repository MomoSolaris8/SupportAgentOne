import pytest
from sqlalchemy import text

from supportagent.core.models import Document
from supportagent.db.session import SessionLocal
from supportagent.rag import index, retrieval
from supportagent.rag.retrieval import retrieve

WATER = [1.0, 0.0] + [0.0] * 1022
CAR = [0.0, 1.0] + [0.0] * 1022


def fake_embed_texts(_client, texts):
    return [WATER if "Wasser" in text else CAR for text in texts]


@pytest.fixture(autouse=True)
def _fake_embeddings(clean_db, monkeypatch):
    for module in (index, retrieval):
        monkeypatch.setattr(module, "get_embedding_client", lambda: None)
        monkeypatch.setattr(module, "embed_texts", fake_embed_texts)


def confluence_page(source_id, title, section):
    return Document(
        text=f"{title}\n\n{section}",
        metadata={"source": "confluence", "source_id": source_id, "title": title},
    )


def jira_issue(source_id, summary):
    return Document(
        text=summary,
        metadata={"source": "jira", "source_id": source_id, "title": summary},
    )


def index_documents(monkeypatch, documents):
    monkeypatch.setattr(index, "collect_documents", lambda: documents)
    index.main()


def test_closest_chunk_comes_first(monkeypatch):
    index_documents(
        monkeypatch,
        [
            confluence_page("page-1", "Wasserschaden", "Fotos senden."),
            jira_issue("issue-1", "Autounfall melden"),
        ],
    )

    chunks = retrieve("Wasser im Keller")

    assert [chunk["document_id"] for chunk in chunks] == ["page-1", "issue-1"]
    assert chunks[0]["content"] == "Wasserschaden\n\nFotos senden."
    assert chunks[0]["metadata"]["source"] == "confluence"
    assert chunks[0]["distance"] == pytest.approx(0.0)


def test_reindexing_updates_chunk_instead_of_duplicating(monkeypatch):
    index_documents(monkeypatch, [confluence_page("page-1", "Wasserschaden", "Alt.")])
    index_documents(monkeypatch, [confluence_page("page-1", "Wasserschaden", "Neu.")])

    chunks = retrieve("Wasser")

    assert [chunk["content"] for chunk in chunks] == ["Wasserschaden\n\nNeu."]


def test_source_filter_only_returns_that_source(monkeypatch):
    index_documents(
        monkeypatch,
        [
            confluence_page("page-1", "Wasserschaden", "Fotos senden."),
            jira_issue("issue-1", "Wasserrohrbruch"),
        ],
    )

    chunks = retrieve("Wasser", source_filter="jira")

    assert [chunk["document_id"] for chunk in chunks] == ["issue-1"]


def test_limit_caps_number_of_chunks(monkeypatch):
    index_documents(
        monkeypatch,
        [jira_issue(f"issue-{n}", f"Autounfall {n}") for n in range(3)],
    )

    assert len(retrieve("Auto", limit=2)) == 2


def test_cosine_search_can_use_hnsw_index():
    with SessionLocal() as session:
        session.execute(text("SET LOCAL enable_seqscan = off"))
        plan = (
            session.execute(
                text(
                    "EXPLAIN SELECT id FROM chunks "
                    "ORDER BY embedding <=> CAST(:q AS vector) LIMIT 5"
                ),
                {"q": str(WATER)},
            )
            .scalars()
            .all()
        )

    assert any("chunks_embedding_hnsw_idx" in line for line in plan)
