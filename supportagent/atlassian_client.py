import base64
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class AtlassianClient:
    """Thin client for real Confluence Cloud + Jira Cloud REST APIs (Basic Auth via API token)."""

    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        token = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict:
        url = f"{self.base_url}{path}"
        if params:
            url += "?" + urlencode(params)
        request = Request(url, headers=self._headers)
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def _delete(self, path: str) -> None:
        url = f"{self.base_url}{path}"
        request = Request(url, headers=self._headers, method="DELETE")
        with urlopen(request):
            pass

    def _post(self, path: str, body: dict | list) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8")
        headers = {**self._headers, "Content-Type": "application/json"}
        request = Request(url, data=data, headers=headers, method="POST")
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_space_id(self, space_key: str) -> str:
        payload = self._get("/wiki/api/v2/spaces", {"keys": space_key})
        return payload["results"][0]["id"]

    def fetch_confluence_pages(self, space_id: str, cursor: str | None = None) -> tuple[list[dict], str | None]:
        params = {"space-id": space_id, "limit": "50", "body-format": "storage"}
        if cursor:
            params["cursor"] = cursor
        payload = self._get("/wiki/api/v2/pages", params)
        next_link = payload.get("_links", {}).get("next")
        return payload["results"], next_link

    def fetch_confluence_labels(self, page_id: str) -> list[str]:
        payload = self._get(f"/wiki/api/v2/pages/{page_id}/labels")
        return [label["name"] for label in payload.get("results", [])]

    def fetch_jira_issues(self, jql: str, next_page_token: str | None = None) -> tuple[list[dict], str | None]:
        params = {
            "jql": jql,
            "maxResults": "50",
            "fields": "summary,description,comment,labels,status,updated,project,issuetype",
        }
        if next_page_token:
            params["nextPageToken"] = next_page_token
        payload = self._get("/rest/api/3/search/jql", params)
        return payload.get("issues", []), payload.get("nextPageToken")

    def create_confluence_page(
        self,
        space_id: str,
        title: str,
        storage_body: str,
        status: str = "current",
        parent_id: str | None = None,
    ) -> dict:
        body = {
            "spaceId": space_id,
            "status": status,
            "title": title,
            "body": {"representation": "storage", "value": storage_body},
        }
        if parent_id:
            body["parentId"] = parent_id
        return self._post("/wiki/api/v2/pages", body)

    def add_confluence_label(self, page_id: str, label: str) -> dict:
        return self._post(f"/wiki/rest/api/content/{page_id}/label", [{"prefix": "global", "name": label}])

    def delete_confluence_page(self, page_id: str) -> None:
        self._delete(f"/wiki/api/v2/pages/{page_id}")

    def create_jira_issue(
        self,
        project_key: str,
        summary: str,
        description_adf: dict,
        issue_type: str = "Task",
        labels: list[str] | None = None,
    ) -> dict:
        body = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": description_adf,
                "issuetype": {"name": issue_type},
                "labels": labels or [],
            }
        }
        return self._post("/rest/api/3/issue", body)

    def add_jira_comment(self, issue_key: str, comment_adf: dict) -> dict:
        return self._post(f"/rest/api/3/issue/{issue_key}/comment", {"body": comment_adf})
