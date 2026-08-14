import asyncio

from supportagent.api import mcp
from supportagent.auth.schemas import AuthUser
from supportagent.mcp_client.store import MCPIdempotencyClaim


def calendar_request():
    return mcp.McpToolCallRequest(
        server="teams_mcp",
        tool="create_default_calendar_event",
        confirmed=True,
        arguments={
            "subject": "Harness agent test 🇩🇪",
            "start_time": "2026-07-21T17:00:00",
            "end_time": "2026-07-21T18:00:00",
            "timezone": "W. Europe Standard Time",
        },
    )


def user():
    return AuthUser(id="user-1", email="operator@example.com", display_name="Operator")


def test_calendar_idempotency_key_is_stable_for_the_same_event():
    first = calendar_request()
    second = calendar_request()
    second.arguments["transaction_id"] = "untrusted-client-value"

    assert mcp._calendar_idempotency_key(first) == mcp._calendar_idempotency_key(second)


def test_calendar_replay_returns_saved_result_without_calling_graph(monkeypatch):
    replayed = '{"subject":"Harness agent test","webLink":"https://outlook.example/event"}'
    monkeypatch.setattr(mcp, "tool_manual_allowed", lambda *args: (True, None))
    monkeypatch.setattr(
        mcp,
        "claim_idempotency_key",
        lambda **kwargs: MCPIdempotencyClaim(status="replay", result=replayed),
    )

    result = asyncio.run(mcp.mcp_call(calendar_request(), user()))

    assert result.result == replayed
    assert result.replayed is True


def test_calendar_execution_records_backend_generated_idempotency_key(monkeypatch):
    captured = {}
    completed = {}

    class Client:
        def __init__(self, configs):
            pass

        async def call_tool(self, server, tool, arguments):
            captured.update(arguments)
            return '{"id":"event-1"}'

    monkeypatch.setattr(mcp, "tool_manual_allowed", lambda *args: (True, None))
    monkeypatch.setattr(
        mcp,
        "claim_idempotency_key",
        lambda **kwargs: MCPIdempotencyClaim(status="execute"),
    )
    monkeypatch.setattr(mcp, "inject_user_credentials", lambda user_id, server, arguments: dict(arguments))
    monkeypatch.setattr(mcp, "local_mcp_configs", lambda servers: [object()])
    monkeypatch.setattr(mcp, "MultiServerMCPClient", Client)
    monkeypatch.setattr(mcp, "add_audit_log", lambda **kwargs: None)
    monkeypatch.setattr(mcp, "record_mcp_action_turn", lambda **kwargs: None)
    monkeypatch.setattr(mcp, "complete_idempotency_key", lambda **kwargs: completed.update(kwargs))

    request = calendar_request()
    expected_key = mcp._calendar_idempotency_key(request)
    asyncio.run(mcp.mcp_call(request, user()))

    assert captured["transaction_id"] == expected_key
    assert completed["idempotency_key"] == expected_key
