import pytest

from supportagent.mcp_servers.http import ToolConfigurationError
from supportagent.mcp_servers.teams_mcp import tools


def test_teams_tool_inventory_matches_reference_shape():
    assert [tool.__name__ for tool in tools.TEAMS_TOOLS] == [
        "get_my_profile",
        "batch_get_user_info",
        "create_calendar",
        "delete_calendar",
        "get_calendar_info",
        "get_calendars_list",
        "update_calendar",
        "create_calendar_event",
        "create_default_calendar_event",
        "append_calendar_event_attendee",
        "get_calendar_event",
        "update_calendar_event",
        "delete_calendar_event",
        "create_document",
        "get_document",
        "create_folder",
        "list_folder_files",
        "list_chats",
        "create_message",
    ]


def test_teams_tools_require_graph_token(monkeypatch):
    monkeypatch.delenv("MS_GRAPH_ACCESS_TOKEN", raising=False)
    with pytest.raises(ToolConfigurationError):
        tools.get_calendars_list("yuheydemann@outlook.de")


def test_create_calendar_posts_to_graph(monkeypatch):
    calls = []

    def fake_request_json(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return {"id": "calendar-1"}

    monkeypatch.setattr(tools, "request_json", fake_request_json)
    result = tools.create_calendar("yuheydemann@outlook.de", "Interview Prep", access_token="token")

    assert result == {"id": "calendar-1"}
    assert calls[0][0] == "POST"
    assert calls[0][1].endswith("/users/yuheydemann%40outlook.de/calendars")
    assert calls[0][2]["json_body"] == {"name": "Interview Prep"}


def test_create_message_posts_to_teams_chat(monkeypatch):
    calls = []

    def fake_request_json(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return {"id": "message-1"}

    monkeypatch.setattr(tools, "request_json", fake_request_json)
    result = tools.create_message("chat-id", "hello", access_token="token")

    assert result == {"id": "message-1"}
    assert calls[0][0] == "POST"
    assert calls[0][1].endswith("/chats/chat-id/messages")
    assert calls[0][2]["json_body"]["body"]["content"] == "hello"
