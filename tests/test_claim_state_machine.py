import pytest

from supportagent.claims.state_machine import (
    action_risk_level,
    initial_action_status,
    validate_action_decision,
    validate_claim_transition,
)


def test_claim_state_machine_allows_review_path():
    validate_claim_transition("DRAFT", "DOCUMENTS_PENDING")
    validate_claim_transition("DOCUMENTS_PENDING", "READY_FOR_REVIEW")
    validate_claim_transition("READY_FOR_REVIEW", "UNDER_REVIEW")


def test_claim_state_machine_rejects_skipped_transition():
    with pytest.raises(ValueError, match="not allowed"):
        validate_claim_transition("DRAFT", "UNDER_REVIEW")


def test_terminal_claim_decisions_are_outside_v01():
    with pytest.raises(ValueError):
        validate_claim_transition("UNDER_REVIEW", "APPROVED")


@pytest.mark.parametrize(
    ("action_type", "risk"),
    [
        ("CREATE_JIRA_ISSUE", "medium"),
        ("SEND_TEAMS_NOTIFICATION", "medium"),
        ("UPDATE_CLAIM_STATUS", "high"),
    ],
)
def test_write_actions_wait_for_approval(action_type, risk):
    assert action_risk_level(action_type) == risk
    assert initial_action_status(action_type) == "WAITING_FOR_APPROVAL"


def test_only_waiting_action_can_be_approved():
    assert validate_action_decision("WAITING_FOR_APPROVAL", "approve") == "APPROVED"
    with pytest.raises(ValueError, match="cannot be approve"):
        validate_action_decision("APPROVED", "approve")


def test_only_waiting_action_can_be_rejected():
    assert validate_action_decision("WAITING_FOR_APPROVAL", "reject") == "REJECTED"
    with pytest.raises(ValueError, match="cannot be reject"):
        validate_action_decision("REJECTED", "reject")
