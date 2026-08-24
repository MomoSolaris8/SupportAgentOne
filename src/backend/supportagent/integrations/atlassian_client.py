import base64
import json
from collections.abc import Iterator
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

# Both APIs are cursor based and neither reports a total, so the only stop
# condition is "no next cursor". A repeated cursor would loop forever, so it is
# treated as the end of the result set as well.
_MAX_PAGES = 1000


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

    @staticmethod
    def _cursor_from_next_link(payload: dict) -> str | None:
        """Confluence returns the next page as a URL, not a bare cursor."""
        next_link = payload.get("_links", {}).get("next")
        if not next_link:
            return None
        cursors = parse_qs(urlparse(next_link).query).get("cursor")
        return cursors[0] if cursors else None

    def fetch_confluence_pages(
        self, space_id: str, cursor: str | None = None, limit: int = 50
    ) -> tuple[list[dict], str | None]:
        """One page of results plus the cursor for the next one (None when done)."""
        params = {"space-id": space_id, "limit": str(limit), "body-format": "storage"}
        if cursor:
            params["cursor"] = cursor
        payload = self._get("/wiki/api/v2/pages", params)
        return payload["results"], self._cursor_from_next_link(payload)

    def iter_confluence_pages(self, space_id: str, limit: int = 50) -> Iterator[dict]:
        """Every page in the space, following cursors until they run out."""
        cursor: str | None = None
        seen_cursors: set[str] = set()
        for _ in range(_MAX_PAGES):
            pages, cursor = self.fetch_confluence_pages(space_id, cursor, limit)
            yield from pages
            if not cursor or cursor in seen_cursors:
                return
            seen_cursors.add(cursor)
        raise RuntimeError(f"confluence pagination exceeded {_MAX_PAGES} requests")

    def fetch_confluence_labels(self, page_id: str) -> list[str]:
        payload = self._get(f"/wiki/api/v2/pages/{page_id}/labels")
        return [label["name"] for label in payload.get("results", [])]

    def fetch_jira_issues(
        self, jql: str, next_page_token: str | None = None, max_results: int = 50
    ) -> tuple[list[dict], str | None]:
        """One page of issues plus the token for the next one (None when done)."""
        params = {
            "jql": jql,
            "maxResults": str(max_results),
            "fields": "summary,description,comment,labels,status,updated,project,issuetype",
        }
        if next_page_token:
            params["nextPageToken"] = next_page_token
        payload = self._get("/rest/api/3/search/jql", params)
        return payload.get("issues", []), payload.get("nextPageToken")

    def iter_jira_issues(self, jql: str, max_results: int = 50) -> Iterator[dict]:
        """Every issue matching the JQL, following nextPageToken until exhausted."""
        token: str | None = None
        seen_tokens: set[str] = set()
        for _ in range(_MAX_PAGES):
            issues, token = self.fetch_jira_issues(jql, token, max_results)
            yield from issues
            if not token or token in seen_tokens:
                return
            seen_tokens.add(token)
        raise RuntimeError(f"jira pagination exceeded {_MAX_PAGES} requests")

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
