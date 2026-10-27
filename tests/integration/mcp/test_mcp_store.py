import pytest


from supportagent.mcp_client.store import (
    MCPIdempotencyClaim,
    abandon_idempotency_key,
    add_audit_log,
    claim_idempotency_key,
    complete_idempotency_key,
    consume_oauth_state,
    get_tool_policy,
    get_user_credentials,
    list_audit_logs,
    list_mcp_servers,
    save_oauth_state,
    upsert_mcp_server,
    upsert_user_credentials,
)

pytestmark = pytest.mark.usefixtures("clean_db")

KEY = {
    "user_id": "user-1",
    "server_name": "calendar",
    "tool_name": "create_event",
    "idempotency_key": "req-1",
}


def add_server(**overrides):
    server = {
        "server_name": "test_mcp",
        "display_name": "Test MCP",
        "transport": "stdio",
        "config": {"command": "python"},
        "enabled": True,
    }
    upsert_mcp_server(**{**server, **overrides})


def listed_server(server_name):
    return {s["server_name"]: s for s in list_mcp_servers()}[server_name]


# db idempotent
def test_first_claim_executes():
    assert claim_idempotency_key(**KEY).status == "execute"


def test_claim_while_in_progress_does_not_execute():
    claim_idempotency_key(**KEY)

    assert claim_idempotency_key(**KEY).status == "in_progress"


def test_completed_key_replays_result():
    claim_idempotency_key(**KEY)
    complete_idempotency_key(**KEY, result="event-123")

    assert claim_idempotency_key(**KEY) == MCPIdempotencyClaim(
        status="replay", result="event-123"
    )


def test_abandoned_key_can_be_claimed_again():
    claim_idempotency_key(**KEY)
    abandon_idempotency_key(**KEY)

    assert claim_idempotency_key(**KEY).status == "execute"


def test_abandon_keeps_completed_key():
    claim_idempotency_key(**KEY)
    complete_idempotency_key(**KEY, result="event-123")
    abandon_idempotency_key(**KEY)

    assert claim_idempotency_key(**KEY).status == "replay"


def test_key_is_scoped_per_user():
    claim_idempotency_key(**KEY)

    other_user = {**KEY, "user_id": "user-2"}
    assert claim_idempotency_key(**other_user).status == "execute"


# OAuth state
def test_oauth_state_can_only_be_used_once():
    save_oauth_state("state-1", "user-1", "microsoft")

    assert consume_oauth_state("state-1", "microsoft") == "user-1"
    assert consume_oauth_state("state-1", "microsoft") is None


def test_oauth_state_is_bound_to_provider():
    save_oauth_state("state-1", "user-1", "microsoft")

    assert consume_oauth_state("state-1", "google") is None


def test_expired_oauth_state_is_rejected():
    save_oauth_state("state-1", "user-1", "microsoft", ttl_minutes=-1)

    assert consume_oauth_state("state-1", "microsoft") is None


def test_saving_same_oauth_state_overwrites_it():
    save_oauth_state("state-1", "user-1", "microsoft")
    save_oauth_state("state-1", "user-2", "microsoft")

    assert consume_oauth_state("state-1", "microsoft") == "user-2"


# servers
def test_added_server_is_listed():
    add_server()

    server = listed_server("test_mcp")
    assert server["config"] == {"command": "python"}
    assert server["enabled"] is True


def test_upserting_existing_server_updates_it():
    add_server()
    add_server(display_name="Renamed", enabled=False)

    server = listed_server("test_mcp")
    assert server["display_name"] == "Renamed"
    assert server["enabled"] is False


# tool policy
def test_unknown_write_tool_requires_confirmation():
    policy = get_tool_policy("test_mcp", "delete_everything")

    assert policy.enabled is True
    assert policy.auto_allowed is False
    assert policy.requires_confirmation is True


# credentials
def test_saved_credentials_are_returned():
    add_server()
    upsert_user_credentials("user-1", "test_mcp", {"access_token": "tok-1"})

    assert get_user_credentials("user-1", "test_mcp") == {"access_token": "tok-1"}


def test_saving_credentials_again_replaces_them():
    add_server()
    upsert_user_credentials("user-1", "test_mcp", {"access_token": "tok-1"})
    upsert_user_credentials("user-1", "test_mcp", {"access_token": "tok-2"})

    assert get_user_credentials("user-1", "test_mcp") == {"access_token": "tok-2"}


def test_missing_credentials_are_empty():
    assert get_user_credentials("user-1", "test_mcp") == {}


# audit log
def test_audit_log_redacts_secrets():
    add_audit_log(
        "user-1",
        "test_mcp",
        "get_weather",
        "success",
        {"city": "Berlin", "access_token": "secret"},
    )

    [record] = list_audit_logs("user-1")
    assert record.arguments == {"city": "Berlin", "access_token": "***"}


def test_audit_logs_are_newest_first_and_per_user():
    add_audit_log("user-1", "test_mcp", "get_weather", "success", {})
    add_audit_log("user-1", "test_mcp", "get_current_time", "success", {})
    add_audit_log("user-2", "test_mcp", "get_weather", "success", {})

    tools = [record.tool_name for record in list_audit_logs("user-1")]
    assert tools == ["get_current_time", "get_weather"]
