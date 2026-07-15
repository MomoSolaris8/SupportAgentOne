import json
import os
from dataclasses import asdict

from dotenv import load_dotenv
from supportagent.adf_utils import adf_to_text
from supportagent.core.models import Document
from supportagent.html_utils import html_to_text
from supportagent.integrations.atlassian_client import AtlassianClient
from supportagent.seed import INSURANCE_KB_LABEL


def confluence_page_to_document(page: dict, base_url: str, labels: list[str]) -> Document:
    body = page.get("body", {}).get("storage", {}).get("value", "")
    text = html_to_text(body)
    return Document(
        text=f"{page['title']}\n\n{text}",
        metadata={
            "source": "confluence",
            "source_id": page["id"],
            "title": page["title"],
            "space_id": page.get("spaceId"),
            "labels": labels,
            "version": page["version"]["number"],
            "updated_at": page["version"]["createdAt"],
            "url": f"{base_url}/wiki{page['_links']['webui']}",
        },
    )


def jira_issue_to_document(issue: dict, base_url: str) -> Document:
    fields = issue["fields"]
    comments = fields.get("comment", {}).get("comments", [])
    comment_text = "\n".join(adf_to_text(comment.get("body")) for comment in comments)
    text = "\n\n".join(
        part
        for part in [
            fields["summary"],
            adf_to_text(fields.get("description")),
            comment_text,
        ]
        if part
    )
    return Document(
        text=text,
        metadata={
            "source": "jira",
            "source_id": issue["id"],
            "issue_key": issue["key"],
            "title": fields["summary"],
            "project_key": fields["project"]["key"],
            "issue_type": fields["issuetype"]["name"],
            "status": fields["status"]["name"],
            "labels": fields.get("labels", []),
            "updated_at": fields["updated"],
            "url": f"{base_url}/browse/{issue['key']}",
        },
    )


def collect_documents() -> list[Document]:
    base_url = os.environ["ATLASSIAN_BASE_URL"]
    email = os.environ["ATLASSIAN_EMAIL"]
    api_token = os.environ["ATLASSIAN_API_TOKEN"]

    client = AtlassianClient(base_url, email, api_token)
    documents: list[Document] = []

    space_key = os.environ.get("CONFLUENCE_SPACE_KEY")
    if space_key:
        space_id = client.get_space_id(space_key)
        pages, _ = client.fetch_confluence_pages(space_id)
        for page in pages:
            labels = client.fetch_confluence_labels(page["id"])
            if INSURANCE_KB_LABEL not in labels:
                continue
            documents.append(confluence_page_to_document(page, base_url, labels))

    jira_project_key = os.environ.get("JIRA_PROJECT_KEY")
    if jira_project_key:
        issues, _ = client.fetch_jira_issues(f"project={jira_project_key}")
        for issue in issues:
            documents.append(jira_issue_to_document(issue, base_url))

    return documents


def main() -> None:
    load_dotenv()
    documents = collect_documents()
    print(json.dumps([asdict(doc) for doc in documents], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
