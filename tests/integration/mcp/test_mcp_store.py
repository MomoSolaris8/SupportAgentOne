import pytest


from supportagent.mcp_client.store import (
    MCPIdempotencyClaim,
    abandon_idempotency_key,
    claim_idempotency_key,
    complete_idempotency_key,
    consume_oauth_state,
    save_oauth_state,
)

pytestmark = pytest.mark.usefixtures("clean_db")

KEY = {
    "user_id": "user-1",
    "server_name": "calendar",
    "tool_name": "create_event",
    "idempotency_key": "req-1",
}


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