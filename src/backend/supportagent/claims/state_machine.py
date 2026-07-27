from supportagent.claims.schemas import ActionStatus, ActionType, ClaimStatus


CLAIM_TRANSITIONS: dict[ClaimStatus, set[ClaimStatus]] = {
    "DRAFT": {"DOCUMENTS_PENDING", "READY_FOR_REVIEW"},
    "DOCUMENTS_PENDING": {"READY_FOR_REVIEW"},
    "READY_FOR_REVIEW": {"UNDER_REVIEW", "NEEDS_INFORMATION"},
    "UNDER_REVIEW": {"READY_FOR_REVIEW", "NEEDS_INFORMATION", "READY_FOR_DECISION"},
    "NEEDS_INFORMATION": {"DOCUMENTS_PENDING", "READY_FOR_REVIEW"},
    "READY_FOR_DECISION": {
        "NEEDS_INFORMATION",
        "EXPERT_REVIEW_REQUIRED",
        "APPROVED",
        "REJECTED",
    },
    "EXPERT_REVIEW_REQUIRED": {"UNDER_REVIEW", "READY_FOR_DECISION"},
    "APPROVED": {"CLOSED"},
    "REJECTED": {"CLOSED"},
    "CLOSED": set(),
}

OUT_OF_SCOPE_STATES: set[ClaimStatus] = {"CLOSED"}


def validate_claim_transition(current: ClaimStatus, target: ClaimStatus) -> None:
    if target not in CLAIM_TRANSITIONS[current]:
        raise ValueError(f"Claim status transition {current} -> {target} is not allowed.")
    if target in OUT_OF_SCOPE_STATES:
        raise ValueError(f"Claim status {target} is outside the v0.1 execution scope.")


def action_risk_level(action_type: ActionType) -> str:
    return "high" if action_type == "UPDATE_CLAIM_STATUS" else "medium"


def initial_action_status(action_type: ActionType) -> ActionStatus:
    # Every v0.1 action is a write. The model can propose it, but deterministic
    # application code must receive a persisted approval before execution.
    _ = action_type
    return "WAITING_FOR_APPROVAL"


def validate_action_decision(current: ActionStatus, decision: str) -> ActionStatus:
    if current != "WAITING_FOR_APPROVAL":
        raise ValueError(f"Action in status {current} cannot be {decision}.")
    if decision == "approve":
        return "APPROVED"
    if decision == "reject":
        return "REJECTED"
    raise ValueError(f"Unknown action decision: {decision}.")
