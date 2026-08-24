"""Cursor handling for the Confluence and Jira list endpoints.

Both APIs cap a response at `limit` results and report no total, so dropping the
cursor truncates the corpus silently - it looks like a complete ingest of a
smaller knowledge base.
"""

import pytest

from supportagent.integrations.atlassian_client import AtlassianClient


class FakeClient(AtlassianClient):
    """Records requests and replays canned payloads instead of doing HTTP."""

    def __init__(self, responses: list[dict]):
        super().__init__("https://example.atlassian.net", "user@example.com", "token")
        self._responses = responses
        self.requests: list[tuple[str, dict]] = []

    def _get(self, path: str, params: dict | None = None) -> dict:
        self.requests.append((path, params or {}))
        return self._responses[len(self.requests) - 1]


def _confluence_payload(page_ids: list[str], next_cursor: str | None) -> dict:
    payload = {"results": [{"id": page_id} for page_id in page_ids]}
    if next_cursor:
        payload["_links"] = {
            "next": f"/wiki/api/v2/pages?limit=50&cursor={next_cursor}&space-id=1"
        }
    return payload


def _jira_payload(issue_ids: list[str], next_token: str | None) -> dict:
    payload = {"issues": [{"id": issue_id} for issue_id in issue_ids]}
    if next_token:
        payload["nextPageToken"] = next_token
    return payload


def test_confluence_cursor_is_parsed_out_of_the_next_link():
    client = FakeClient([_confluence_payload(["1"], next_cursor="abc123")])

    _, cursor = client.fetch_confluence_pages("space-1")

    assert cursor == "abc123"


def test_confluence_cursor_is_none_on_the_last_page():
    client = FakeClient([_confluence_payload(["1"], next_cursor=None)])

    _, cursor = client.fetch_confluence_pages("space-1")

    assert cursor is None


def test_iter_confluence_pages_follows_every_cursor():
    client = FakeClient(
        [
            _confluence_payload(["1", "2"], next_cursor="c2"),
            _confluence_payload(["3", "4"], next_cursor="c3"),
            _confluence_payload(["5"], next_cursor=None),
        ]
    )

    pages = list(client.iter_confluence_pages("space-1", limit=2))

    assert [page["id"] for page in pages] == ["1", "2", "3", "4", "5"]
    assert [params.get("cursor") for _, params in client.requests] == [None, "c2", "c3"]


def test_iter_confluence_pages_stops_on_a_repeated_cursor():
    """A server that keeps handing back the same cursor must not loop forever."""
    client = FakeClient([_confluence_payload(["1"], next_cursor="same")] * 5)

    pages = list(client.iter_confluence_pages("space-1"))

    assert [page["id"] for page in pages] == ["1", "1"]


def test_iter_jira_issues_follows_every_page_token():
    client = FakeClient(
        [
            _jira_payload(["1", "2"], next_token="t2"),
            _jira_payload(["3"], next_token=None),
        ]
    )

    issues = list(client.iter_jira_issues("project=SUP"))

    assert [issue["id"] for issue in issues] == ["1", "2", "3"]
    assert [params.get("nextPageToken") for _, params in client.requests] == [None, "t2"]


def test_iter_jira_issues_stops_on_a_repeated_token():
    client = FakeClient([_jira_payload(["1"], next_token="same")] * 5)

    issues = list(client.iter_jira_issues("project=SUP"))

    assert [issue["id"] for issue in issues] == ["1", "1"]


@pytest.mark.parametrize(
    "iterate",
    [
        lambda client: client.iter_confluence_pages("space-1"),
        lambda client: client.iter_jira_issues("project=SUP"),
    ],
)
def test_single_page_result_issues_exactly_one_request(iterate):
    client = FakeClient(
        [{"results": [{"id": "1"}], "issues": [{"id": "1"}]}]
    )

    assert len(list(iterate(client))) == 1
    assert len(client.requests) == 1
