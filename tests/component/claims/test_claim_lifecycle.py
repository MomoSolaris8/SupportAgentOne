from datetime import datetime, timezone

import pytest

from pydantic import ValidationError

from supportagent.claims.schemas import (
    Claim,
    ClaimDecisionRequest,
    ClaimDocument,
    ClaimReviewResponse,
)


class FakeConnection:
    def commit(self) -> None:
        pass

    def close(self) -> None:
        pass


def claim(status: str = "DRAFT") -> Claim:
    return Claim(
        id="claim-1",
        owner_user_id="user-1",
        policy_id="POL-1",
        product_line="residential_building",
        policy_version="2026.1",
        jurisdiction="DE",
        customer_reference="CUSTOMER-1",
        claim_type="water_damage",
        status=status,
        created_at="2026-07-21T00:00:00+00:00",
        updated_at="2026-07-21T00:00:00+00:00",
    )


def document(document_type: str) -> ClaimDocument:
    return ClaimDocument(
        id=f"doc-{document_type}",
        claim_id="claim-1",
        document_type=document_type,
        filename=f"{document_type}.pdf",
        extraction_status="COMPLETED",
        created_at="2026-07-21T00:00:00+00:00",
    )


def configure_service(monkeypatch, *, current_claim: Claim, documents: list[ClaimDocument]):
    from supportagent.claims import service

    monkeypatch.setattr(service, "get_connection", lambda: FakeConnection())
    monkeypatch.setattr(service, "fetch_claim", lambda conn, claim_id, owner_user_id: current_claim)
    monkeypatch.setattr(service, "fetch_documents", lambda conn, claim_id: documents)
    monkeypatch.setattr(service, "add_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        service,
        "update_claim_status",
        lambda conn, claim_id, status: current_claim.model_copy(update={"status": status}),
    )
    return service


def test_complete_draft_submission_becomes_ready_for_review(monkeypatch):
    complete_documents = [
        document("claim_form"),
        document("damage_cause_report"),
        document("damage_photo"),
        document("repair_invoice"),
    ]
    service = configure_service(
        monkeypatch,
        current_claim=claim(),
        documents=complete_documents,
    )

    result = service.submit_claim_for_review("claim-1", "user-1")

    assert result.claim.status == "READY_FOR_REVIEW"
    assert result.missing_documents == []


def test_incomplete_draft_submission_becomes_documents_pending(monkeypatch):
    service = configure_service(
        monkeypatch,
        current_claim=claim(),
        documents=[document("claim_form")],
    )

    result = service.submit_claim_for_review("claim-1", "user-1")

    assert result.claim.status == "DOCUMENTS_PENDING"
    assert result.missing_documents == [
        "damage_cause_report",
        "damage_photo",
        "repair_invoice",
    ]


def test_review_can_only_start_when_claim_is_ready(monkeypatch):
    from supportagent.claims import service

    configure_service(monkeypatch, current_claim=claim("DRAFT"), documents=[])

    with pytest.raises(service.ClaimStateConflictError, match="not ready"):
        service.start_claim_review_run("claim-1", "user-1")


def test_successful_supported_review_becomes_ready_for_decision(monkeypatch):
    from supportagent.claims import service

    current_claim = claim("UNDER_REVIEW")
    configure_service(monkeypatch, current_claim=current_claim, documents=[])
    transitions: list[str] = []
    monkeypatch.setattr(
        service,
        "update_claim_status",
        lambda conn, claim_id, status: (
            transitions.append(status) or current_claim.model_copy(update={"status": status})
        ),
    )
    completed_run = type(
        "Run",
        (),
        {
            "id": "run-1",
            "claim_id": "claim-1",
            "status": "SUCCEEDED",
            "current_step": "COMPLETED",
            "result": None,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
    )()
    monkeypatch.setattr(service, "update_review_run", lambda *args, **kwargs: completed_run)

    result = ClaimReviewResponse(
        run_id="run-1",
        claim_id="claim-1",
        required_documents=[],
        present_documents=[],
        missing_documents=[],
        optional_documents=[],
        conditional_documents=[],
        evidence_status="sufficient",
        evidence_reason="Approved evidence retrieved.",
        recommendation="Continue manual review.",
    )

    run = service.complete_claim_review_run(result, "user-1")

    assert run.status == "SUCCEEDED"
    assert transitions == ["READY_FOR_DECISION"]


@pytest.mark.parametrize(
    ("decision", "target_status"),
    [("APPROVE", "APPROVED"), ("REJECT", "REJECTED")],
)
def test_human_decision_updates_claim_and_writes_audit(
    monkeypatch, decision, target_status
):
    current_claim = claim("READY_FOR_DECISION")
    service = configure_service(monkeypatch, current_claim=current_claim, documents=[])
    transitions: list[str] = []
    audit_events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        service,
        "update_claim_status",
        lambda conn, claim_id, status: (
            transitions.append(status)
            or current_claim.model_copy(update={"status": status})
        ),
    )
    monkeypatch.setattr(
        service,
        "add_audit_event",
        lambda conn, claim_id, actor_user_id, event_type, payload: audit_events.append(
            (event_type, payload)
        ),
    )

    result = service.apply_human_claim_decision(
        "claim-1",
        "user-1",
        ClaimDecisionRequest(
            decision=decision,
            reason="Reviewed by a human operator.",
        ),
    )

    assert result.status == target_status
    assert transitions == [target_status]
    assert audit_events[-1][0] == "CLAIM_HUMAN_DECISION_RECORDED"
    assert audit_events[-1][1]["decision_source"] == "HUMAN"


def test_rejecting_claim_requires_a_reason():
    with pytest.raises(ValidationError, match="reason is required"):
        ClaimDecisionRequest(decision="REJECT")
