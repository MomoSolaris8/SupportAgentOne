import json
import os
from pathlib import Path

from .adf_utils import text_to_adf
from supportagent.integrations.atlassian_client import AtlassianClient
from dotenv import load_dotenv
from .seed_content import CONFLUENCE_PAGES, JIRA_ISSUES, PROJECTS

ROOT = Path(__file__).resolve().parents[1]
PDF_PAGES_FILE = ROOT / "data" / "confluence_pages_from_pdf.json"

# Marks pages created by this script so ingest.py can filter out the
# unrelated default/template pages that already exist in the space.
INSURANCE_KB_LABEL = "insurance-kb"


def load_confluence_pages() -> list[dict]:
    pages = list(CONFLUENCE_PAGES)
    if PDF_PAGES_FILE.exists():
        pages.extend(json.loads(PDF_PAGES_FILE.read_text()))
    return pages


def main() -> None:
    load_dotenv()

    base_url = os.environ["ATLASSIAN_BASE_URL"]
    email = os.environ["ATLASSIAN_EMAIL"]
    api_token = os.environ["ATLASSIAN_API_TOKEN"]
    space_key = os.environ["CONFLUENCE_SPACE_KEY"]
    jira_project_key = os.environ.get("JIRA_PROJECT_KEY")

    client = AtlassianClient(base_url, email, api_token)
    space_id = client.get_space_id(space_key)

    project_page_ids: dict[str, str] = {}
    for project in PROJECTS:
        result = client.create_confluence_page(space_id, project["title"], project["body"])
        page_id = result["id"]
        project_page_ids[project["key"]] = page_id
        client.add_confluence_label(page_id, INSURANCE_KB_LABEL)
        print(f"Created project page: {project['title']} ({page_id})")

    for page in load_confluence_pages():
        parent_id = project_page_ids.get(page.get("project"))
        result = client.create_confluence_page(space_id, page["title"], page["body"], parent_id=parent_id)
        page_id = result["id"]
        for label in [*page["labels"], INSURANCE_KB_LABEL]:
            client.add_confluence_label(page_id, label)
        print(f"Created Confluence page: {page['title']} ({page_id})")

    if jira_project_key:
        for issue in JIRA_ISSUES:
            result = client.create_jira_issue(
                jira_project_key,
                issue["summary"],
                text_to_adf(issue["description"]),
                issue_type=issue.get("issue_type", "Task"),
                labels=issue.get("labels", []),
            )
            issue_key = result["key"]
            for comment in issue.get("comments", []):
                client.add_jira_comment(issue_key, text_to_adf(comment))
            print(f"Created Jira issue: {issue['summary']} ({issue_key})")


if __name__ == "__main__":
    main()
