from uuid import uuid4

from sqlalchemy.orm import Session

from supportagent.claims.schemas import (
    Claim,
    ClaimDetail,
    ClaimDocument,
    ClaimDecisionRequest,
    ClaimNextStepRequest,
    ClaimReviewResponse,
    ClaimReviewRun,
    ClaimSubmissionResponse,
    CreateClaimDocumentRequest,
    CreateClaimRequest,
    CreateProposedActionRequest,
    ProposedAction,
)
from supportagent.claims.state_machine import (
    action_risk_level,
    initial_action_status,
    validate_action_decision,
    validate_claim_transition,
)
from supportagent.claims.store import (
    add_audit_event,
    fetch_audit_events,
    fetch_action_for_owner,
    fetch_actions,
    fetch_claim,
    fetch_claims,
    fetch_documents,
    fetch_latest_review_run,
    fetch_review_run_for_owner,
    insert_action,
    insert_claim,
    insert_document,
    insert_review_run,
    record_action_decision,
    update_claim_status,
    update_review_run,
)
from supportagent.db.session import SessionLocal


class ClaimNotFoundError(LookupError):
    pass


class ClaimActionConflictError(ValueError):
    pass


class ClaimStateConflictError(ValueError):
    pass


def create_claim(owner_user_id: str, request: CreateClaimRequest) -> Claim:
    with SessionLocal.begin() as session:
        claim = insert_claim(
            session,
            {
                "id": str(uuid4()),
                "owner_user_id": owner_user_id,
                "policy_id": request.policy_id,
                "product_line": request.product_line,
                "policy_version": request.policy_version,
                "jurisdiction": request.jurisdiction,
                "customer_reference": request.customer_reference,
                "claim_type": request.claim_type,
                "incident_date": request.incident_date,
                "status": "DRAFT",
            },
        )
        add_audit_event(session, claim.id, owner_user_id, "CLAIM_CREATED", {"status": claim.status})
        return claim


def list_claims(owner_user_id: str) -> list[Claim]:
    with SessionLocal() as session:
        return fetch_claims(session, owner_user_id)


def get_claim(claim_id: str, owner_user_id: str) -> ClaimDetail:
    with SessionLocal() as session:
        claim = fetch_claim(session, claim_id, owner_user_id)
        if claim is None:
            raise ClaimNotFoundError("Claim not found.")
        return ClaimDetail(
            claim=claim,
            documents=fetch_documents(session, claim_id),
            proposed_actions=fetch_actions(session, claim_id),
            latest_review_run=fetch_latest_review_run(session, claim_id, owner_user_id),
            audit_events=fetch_audit_events(session, claim_id),
        )


def _transition_claim(
    session: Session,
    claim: Claim,
    target_status: str,
    actor_user_id: str,
    *,
    reason: str,
) -> Claim:
    if claim.status == target_status:
        return claim
    try:
        validate_claim_transition(claim.status, target_status)
    except ValueError as error:
        raise ClaimStateConflictError(str(error)) from error
    updated = update_claim_status(session, claim.id, target_status)
    add_audit_event(
        session,
        claim.id,
        actor_user_id,
        "CLAIM_STATUS_CHANGED",
        {"from": claim.status, "to": target_status, "reason": reason},
    )
    return updated


def submit_claim_for_review(claim_id: str, owner_user_id: str) -> ClaimSubmissionResponse:
    from supportagent.claims.document_rules import completed_document_types, missing_documents_for_claim

    with SessionLocal.begin() as session:
        claim = fetch_claim(session, claim_id, owner_user_id)
        if claim is None:
            raise ClaimNotFoundError("Claim not found.")
        if claim.status not in {"DRAFT", "DOCUMENTS_PENDING", "NEEDS_INFORMATION"}:
            raise ClaimStateConflictError(
                f"Claim in status {claim.status} cannot be submitted for review."
            )
        documents = fetch_documents(session, claim_id)
        present = completed_document_types(documents)
        missing = missing_documents_for_claim(claim, documents)
        target_status = "DOCUMENTS_PENDING" if missing else "READY_FOR_REVIEW"
        updated = _transition_claim(
            session,
            claim,
            target_status,
            owner_user_id,
            reason="Submission document validation completed.",
        )
        add_audit_event(
            session,
            claim_id,
            owner_user_id,
            "CLAIM_SUBMISSION_VALIDATED",
            {
                "present_documents": present,
                "missing_documents": missing,
                "target_status": target_status,
            },
        )
        return ClaimSubmissionResponse(
            claim=updated,
            present_documents=present,
            missing_documents=missing,
        )


def start_claim_review_run(claim_id: str, owner_user_id: str) -> ClaimReviewRun:
    with SessionLocal.begin() as session:
        claim = fetch_claim(session, claim_id, owner_user_id)
        if claim is None:
            raise ClaimNotFoundError("Claim not found.")
        if claim.status != "READY_FOR_REVIEW":
            raise ClaimStateConflictError(
                f"Claim in status {claim.status} is not ready for review."
            )
        latest = fetch_latest_review_run(session, claim_id, owner_user_id)
        if latest and latest.status in {"QUEUED", "RUNNING"}:
            raise ClaimStateConflictError("A review is already running for this claim.")
        run_id = str(uuid4())
        _transition_claim(
            session,
            claim,
            "UNDER_REVIEW",
            owner_user_id,
            reason="Claim review started.",
        )
        run = insert_review_run(
            session,
            run_id,
            claim_id,
            owner_user_id,
            status="RUNNING",
            current_step="LOAD_CLAIM",
        )
        add_audit_event(
            session,
            claim_id,
            owner_user_id,
            "CLAIM_REVIEW_STARTED",
            {"run_id": run_id},
        )
        return run


def get_claim_review_run(
    claim_id: str, run_id: str, owner_user_id: str
) -> ClaimReviewRun:
    with SessionLocal() as session:
        run = fetch_review_run_for_owner(session, run_id, claim_id, owner_user_id)
        if run is None:
            raise ClaimNotFoundError("Claim review run not found.")
        return run


def record_claim_review_progress(
    claim_id: str,
    run_id: str,
    owner_user_id: str,
    step: str,
) -> None:
    with SessionLocal.begin() as session:
        update_review_run(session, run_id, status="RUNNING", current_step=step)
        add_audit_event(
            session,
            claim_id,
            owner_user_id,
            "CLAIM_REVIEW_PROGRESS",
            {"run_id": run_id, "step": step},
        )


def complete_claim_review_run(
    result: ClaimReviewResponse,
    owner_user_id: str,
) -> ClaimReviewRun:
    with SessionLocal.begin() as session:
        claim = fetch_claim(session, result.claim_id, owner_user_id)
        if claim is None:
            raise ClaimNotFoundError("Claim not found.")
        target_status = (
            "NEEDS_INFORMATION"
            if result.missing_documents or result.evidence_status == "insufficient"
            else "READY_FOR_DECISION"
        )
        _transition_claim(
            session,
            claim,
            target_status,
            owner_user_id,
            reason="Claim review completed.",
        )
        run = update_review_run(
            session,
            result.run_id,
            status="SUCCEEDED",
            current_step="COMPLETED",
            result=result.model_dump(mode="json"),
            complete=True,
        )
        add_audit_event(
            session,
            result.claim_id,
            owner_user_id,
            "CLAIM_REVIEW_COMPLETED",
            {
                "run_id": result.run_id,
                "evidence_status": result.evidence_status,
                "missing_documents": result.missing_documents,
                "target_status": target_status,
            },
        )
        return run


def fail_claim_review_run(
    claim_id: str,
    run_id: str,
    owner_user_id: str,
    error: str,
) -> None:
    with SessionLocal.begin() as session:
        claim = fetch_claim(session, claim_id, owner_user_id)
        if claim is not None and claim.status == "UNDER_REVIEW":
            _transition_claim(
                session,
                claim,
                "READY_FOR_REVIEW",
                owner_user_id,
                reason="Claim review failed and can be retried.",
            )
        update_review_run(
            session,
            run_id,
            status="FAILED",
            current_step="FAILED",
            error=error,
            complete=True,
        )
        add_audit_event(
            session,
            claim_id,
            owner_user_id,
            "CLAIM_REVIEW_FAILED",
            {"run_id": run_id, "error": error[:500]},
        )


def apply_claim_next_step(
    claim_id: str,
    owner_user_id: str,
    request: ClaimNextStepRequest,
) -> Claim:
    with SessionLocal.begin() as session:
        claim = fetch_claim(session, claim_id, owner_user_id)
        if claim is None:
            raise ClaimNotFoundError("Claim not found.")
        if claim.status != "READY_FOR_DECISION":
            raise ClaimStateConflictError(
                f"Claim in status {claim.status} has no decision-ready next step."
            )
        target_status = (
            "NEEDS_INFORMATION"
            if request.next_step == "REQUEST_INFORMATION"
            else "EXPERT_REVIEW_REQUIRED"
        )
        updated = _transition_claim(
            session,
            claim,
            target_status,
            owner_user_id,
            reason=request.comment or request.next_step,
        )
        add_audit_event(
            session,
            claim_id,
            owner_user_id,
            "CLAIM_NEXT_STEP_SELECTED",
            {
                "next_step": request.next_step,
                "comment": request.comment,
            },
        )
        return updated


def apply_human_claim_decision(
    claim_id: str,
    owner_user_id: str,
    request: ClaimDecisionRequest,
) -> Claim:
    with SessionLocal.begin() as session:
        claim = fetch_claim(session, claim_id, owner_user_id)
        if claim is None:
            raise ClaimNotFoundError("Claim not found.")
        if claim.status != "READY_FOR_DECISION":
            raise ClaimStateConflictError(
                f"Claim in status {claim.status} is not ready for a human decision."
            )
        target_status = "APPROVED" if request.decision == "APPROVE" else "REJECTED"
        updated = _transition_claim(
            session,
            claim,
            target_status,
            owner_user_id,
            reason=request.reason or "Approved after human review.",
        )
        add_audit_event(
            session,
            claim_id,
            owner_user_id,
            "CLAIM_HUMAN_DECISION_RECORDED",
            {
                "decision": request.decision,
                "reason": request.reason,
                "decision_source": "HUMAN",
            },
        )
        return updated


def create_claim_document(
    claim_id: str, owner_user_id: str, request: CreateClaimDocumentRequest
) -> ClaimDocument:
    with SessionLocal.begin() as session:
        if fetch_claim(session, claim_id, owner_user_id) is None:
            raise ClaimNotFoundError("Claim not found.")
        document = insert_document(
            session,
            {
                "id": str(uuid4()),
                "claim_id": claim_id,
                **request.model_dump(),
            },
        )
        add_audit_event(
            session, claim_id, owner_user_id, "CLAIM_DOCUMENT_REGISTERED",
            {"document_id": document.id, "document_type": document.document_type},
        )
        return document


def create_proposed_action(
    claim_id: str, owner_user_id: str, request: CreateProposedActionRequest
) -> ProposedAction:
    with SessionLocal.begin() as session:
        if fetch_claim(session, claim_id, owner_user_id) is None:
            raise ClaimNotFoundError("Claim not found.")
        action = insert_action(
            session,
            {
                "id": str(uuid4()),
                "claim_id": claim_id,
                **request.model_dump(),
                "risk_level": action_risk_level(request.action_type),
                "status": initial_action_status(request.action_type),
                "proposed_by": owner_user_id,
            },
        )
        add_audit_event(
            session, claim_id, owner_user_id, "ACTION_PROPOSED",
            {"action_id": action.id, "action_type": action.action_type, "risk_level": action.risk_level},
        )
        return action


def _decide_action(
    claim_id: str, action_id: str, owner_user_id: str, decision: str, comment: str | None
) -> ProposedAction:
    with SessionLocal.begin() as session:
        action = fetch_action_for_owner(session, action_id, claim_id, owner_user_id, for_update=True)
        if action is None:
            raise ClaimNotFoundError("Proposed action not found.")
        try:
            next_status = validate_action_decision(action.status, decision)
        except ValueError as error:
            raise ClaimActionConflictError(str(error)) from error
        updated = record_action_decision(session, action_id, owner_user_id, next_status, comment)
        add_audit_event(
            session, claim_id, owner_user_id, f"ACTION_{next_status}",
            {"action_id": action_id, "comment": comment},
        )
        return updated


def approve_action(
    claim_id: str, action_id: str, owner_user_id: str, comment: str | None = None
) -> ProposedAction:
    return _decide_action(claim_id, action_id, owner_user_id, "approve", comment)


def reject_action(
    claim_id: str, action_id: str, owner_user_id: str, comment: str | None = None
) -> ProposedAction:
    return _decide_action(claim_id, action_id, owner_user_id, "reject", comment)
