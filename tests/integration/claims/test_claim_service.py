import pytest

from supportagent.claims.schemas import (
    ClaimDecisionRequest,
    ClaimReviewResponse,
    CreateClaimDocumentRequest,
    CreateClaimRequest,
    CreateProposedActionRequest,
)
from supportagent.claims.service import (
    ClaimActionConflictError,
    ClaimNotFoundError,
    ClaimStateConflictError,
    apply_human_claim_decision,
    approve_action,
    complete_claim_review_run,
    create_claim,
    create_claim_document,
    create_proposed_action,
    fail_claim_review_run,
    get_claim,
    get_claim_review_run,
    list_claims,
    record_claim_review_progress,
    reject_action,
    start_claim_review_run,
    submit_claim_for_review,
)

COMPLETE_DOCUMENTS = ["claim_form", "damage_cause_report", "damage_photo", "repair_invoice"]


@pytest.fixture(autouse=True)
def _clean(clean_db):
    pass


def new_claim(owner="alice"):
    return create_claim(
        owner,
        CreateClaimRequest(
            policy_id="POL-1",
            product_line="residential_building",
            customer_reference="CUSTOMER-1",
            claim_type="water_damage",
        ),
    )


def add_documents(claim_id, document_types, owner="alice"):
    for document_type in document_types:
        create_claim_document(
            claim_id,
            owner,
            CreateClaimDocumentRequest(
                document_type=document_type,
                filename=f"{document_type}.pdf",
                extraction_status="COMPLETED",
                extracted_fields={"source": document_type},
            ),
        )


def ready_for_review_claim():
    claim = new_claim()
    add_documents(claim.id, COMPLETE_DOCUMENTS)
    submit_claim_for_review(claim.id, "alice")
    return claim


def review_result(run, missing_documents=()):
    return ClaimReviewResponse(
        run_id=run.id,
        claim_id=run.claim_id,
        required_documents=COMPLETE_DOCUMENTS,
        present_documents=COMPLETE_DOCUMENTS,
        missing_documents=list(missing_documents),
        optional_documents=[],
        conditional_documents=[],
        evidence_status="sufficient",
        evidence_reason="All required documents are present.",
        recommendation="Ready for a human decision.",
    )


def ready_for_decision_claim():
    claim = ready_for_review_claim()
    run = start_claim_review_run(claim.id, "alice")
    complete_claim_review_run(review_result(run), "alice")
    return claim


def event_types(claim_id):
    return {event.event_type for event in get_claim(claim_id, "alice").audit_events}


def update_status_action(claim_id, owner="alice"):
    return create_proposed_action(
        claim_id,
        owner,
        CreateProposedActionRequest(
            action_type="UPDATE_CLAIM_STATUS",
            tool_server="claims",
            tool_name="update_claim_status",
            arguments={"status": "APPROVED"},
            reason="Documents complete.",
        ),
    )


# create and read
def test_new_claim_starts_as_draft_and_is_audited():
    claim = new_claim()

    detail = get_claim(claim.id, "alice")

    assert detail.claim.status == "DRAFT"
    assert detail.claim.jurisdiction == "DE"
    assert "CLAIM_CREATED" in event_types(claim.id)


def test_claims_are_only_visible_to_owner():
    claim = new_claim()

    assert [c.id for c in list_claims("alice")] == [claim.id]
    assert list_claims("bob") == []
    with pytest.raises(ClaimNotFoundError):
        get_claim(claim.id, "bob")


def test_other_user_cannot_add_documents():
    claim = new_claim()

    with pytest.raises(ClaimNotFoundError):
        add_documents(claim.id, ["claim_form"], owner="bob")
    assert get_claim(claim.id, "alice").documents == []


# submission
def test_submission_with_missing_documents_waits_for_documents():
    claim = new_claim()
    add_documents(claim.id, ["claim_form"])

    result = submit_claim_for_review(claim.id, "alice")

    assert result.claim.status == "DOCUMENTS_PENDING"
    assert "damage_photo" in result.missing_documents


def test_complete_submission_is_ready_for_review():
    claim = new_claim()
    add_documents(claim.id, COMPLETE_DOCUMENTS)

    result = submit_claim_for_review(claim.id, "alice")

    assert result.claim.status == "READY_FOR_REVIEW"
    assert result.missing_documents == []
    documents = get_claim(claim.id, "alice").documents
    assert documents[0].extracted_fields == {"source": "claim_form"}


# review runs
def test_review_run_moves_claim_to_decision():
    claim = ready_for_review_claim()

    run = start_claim_review_run(claim.id, "alice")
    assert run.status == "RUNNING"
    assert get_claim(claim.id, "alice").claim.status == "UNDER_REVIEW"

    record_claim_review_progress(claim.id, run.id, "alice", "CHECK_DOCUMENTS")
    assert get_claim_review_run(claim.id, run.id, "alice").current_step == "CHECK_DOCUMENTS"

    finished = complete_claim_review_run(review_result(run), "alice")

    assert finished.status == "SUCCEEDED"
    assert finished.completed_at is not None
    assert finished.result.evidence_status == "sufficient"
    assert get_claim(claim.id, "alice").claim.status == "READY_FOR_DECISION"


def test_review_with_missing_documents_needs_information():
    claim = ready_for_review_claim()
    run = start_claim_review_run(claim.id, "alice")

    complete_claim_review_run(review_result(run, missing_documents=["repair_invoice"]), "alice")

    assert get_claim(claim.id, "alice").claim.status == "NEEDS_INFORMATION"


def test_second_review_cannot_start_while_one_is_running():
    claim = ready_for_review_claim()
    start_claim_review_run(claim.id, "alice")

    with pytest.raises(ClaimStateConflictError):
        start_claim_review_run(claim.id, "alice")


def test_failed_review_can_be_retried():
    claim = ready_for_review_claim()
    run = start_claim_review_run(claim.id, "alice")

    fail_claim_review_run(claim.id, run.id, "alice", "LLM timeout")

    failed = get_claim_review_run(claim.id, run.id, "alice")
    assert (failed.status, failed.error) == ("FAILED", "LLM timeout")
    assert get_claim(claim.id, "alice").claim.status == "READY_FOR_REVIEW"
    retry = start_claim_review_run(claim.id, "alice")
    assert get_claim(claim.id, "alice").latest_review_run.id == retry.id


def test_other_user_cannot_read_review_run():
    claim = ready_for_review_claim()
    run = start_claim_review_run(claim.id, "alice")

    with pytest.raises(ClaimNotFoundError):
        get_claim_review_run(claim.id, run.id, "bob")


# human decision
def test_human_decision_approves_claim():
    claim = ready_for_decision_claim()

    updated = apply_human_claim_decision(
        claim.id, "alice", ClaimDecisionRequest(decision="APPROVE")
    )

    assert updated.status == "APPROVED"
    assert "CLAIM_HUMAN_DECISION_RECORDED" in event_types(claim.id)


# proposed actions
def test_proposed_action_waits_for_approval():
    claim = new_claim()

    action = update_status_action(claim.id)

    assert (action.status, action.risk_level) == ("WAITING_FOR_APPROVAL", "high")
    assert action.arguments == {"status": "APPROVED"}


def test_approving_action_records_approver():
    claim = new_claim()
    action = update_status_action(claim.id)

    approved = approve_action(claim.id, action.id, "alice", "Looks good")

    assert approved.status == "APPROVED"
    assert approved.approved_by == "alice"
    assert approved.approved_at is not None
    assert "ACTION_APPROVED" in event_types(claim.id)


def test_rejecting_action_clears_approver():
    claim = new_claim()
    action = update_status_action(claim.id)

    rejected = reject_action(claim.id, action.id, "alice", "Not yet")

    assert rejected.status == "REJECTED"
    assert rejected.approved_by is None


def test_action_cannot_be_decided_twice():
    claim = new_claim()
    action = update_status_action(claim.id)
    approve_action(claim.id, action.id, "alice")

    with pytest.raises(ClaimActionConflictError):
        reject_action(claim.id, action.id, "alice")


def test_other_user_cannot_approve_action():
    claim = new_claim()
    action = update_status_action(claim.id)

    with pytest.raises(ClaimNotFoundError):
        approve_action(claim.id, action.id, "bob")
