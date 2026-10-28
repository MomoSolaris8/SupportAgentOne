from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from supportagent.claims.schemas import (
    Claim,
    ClaimAuditEvent,
    ClaimDocument,
    ClaimReviewRun,
    ProposedAction,
)

from supportagent.db.models import Claim as ClaimRow
from supportagent.db.models import ClaimActionApproval
from supportagent.db.models import ClaimAuditEvent as ClaimAuditEventRow
from supportagent.db.models import ClaimDocument as ClaimDocumentRow
from supportagent.db.models import ClaimReviewRun as ClaimReviewRunRow
from supportagent.db.models import ProposedAction as ProposedActionRow


def _claim(row: ClaimRow) -> Claim:
    return Claim(
        id=row.id,
        owner_user_id=row.owner_user_id,
        policy_id=row.policy_id,
        customer_reference=row.customer_reference,
        claim_type=row.claim_type,
        incident_date=row.incident_date,
        status=row.status,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
        product_line=row.product_line,
        policy_version=row.policy_version,
        jurisdiction=row.jurisdiction,
    )


def _document(row: ClaimDocumentRow) -> ClaimDocument:
    return ClaimDocument(
        id=row.id,
        claim_id=row.claim_id,
        uploaded_file_id=row.uploaded_file_id,
        document_type=row.document_type,
        filename=row.filename,
        extraction_status=row.extraction_status,
        extracted_fields=row.extracted_fields or {},
        created_at=row.created_at.isoformat(),
    )


def _action(row: ProposedActionRow) -> ProposedAction:
    return ProposedAction(
        id=row.id,
        claim_id=row.claim_id,
        run_id=row.run_id,
        action_type=row.action_type,
        tool_server=row.tool_server,
        tool_name=row.tool_name,
        arguments=row.arguments or {},
        reason=row.reason,
        risk_level=row.risk_level,
        status=row.status,
        proposed_by=row.proposed_by,
        approved_by=row.approved_by,
        approved_at=row.approved_at.isoformat() if row.approved_at else None,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )


def _review_run(row: ClaimReviewRunRow) -> ClaimReviewRun:
    return ClaimReviewRun(
        id=row.id,
        claim_id=row.claim_id,
        status=row.status,
        current_step=row.current_step,
        result=row.result,
        error=row.error,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
    )


def _audit_event(row: ClaimAuditEventRow) -> ClaimAuditEvent:
    return ClaimAuditEvent(
        id=row.id,
        event_type=row.event_type,
        payload=row.payload or {},
        actor_user_id=row.actor_user_id,
        created_at=row.created_at.isoformat(),
    )


def insert_claim(session: Session, values: dict[str, Any]) -> Claim:
    row = ClaimRow(
        id=values["id"],
        owner_user_id=values["owner_user_id"],
        policy_id=values["policy_id"],
        customer_reference=values["customer_reference"],
        claim_type=values["claim_type"],
        incident_date=values.get("incident_date"),
        status=values["status"],
        product_line=values["product_line"],
        policy_version=values.get("policy_version"),
        jurisdiction=values["jurisdiction"],
    )
    session.add(row)
    session.flush()
    return _claim(row)


def fetch_claim(session: Session, claim_id: str, owner_user_id: str) -> Claim | None:
    row = session.scalar(
        select(ClaimRow).where(
            ClaimRow.id == claim_id, ClaimRow.owner_user_id == owner_user_id
        )
    )
    return _claim(row) if row else None


def fetch_claims(session: Session, owner_user_id: str) -> list[Claim]:
    rows = session.scalars(
        select(ClaimRow)
        .where(ClaimRow.owner_user_id == owner_user_id)
        .order_by(ClaimRow.updated_at.desc())
    )
    return [_claim(row) for row in rows]


def update_claim_status(session: Session, claim_id: str, status: str) -> Claim:
    row = session.scalar(
        update(ClaimRow)
        .where(ClaimRow.id == claim_id)
        .values(status=status, updated_at=func.now())
        .returning(ClaimRow)
    )
    return _claim(row)


def insert_document(session: Session, values: dict[str, Any]) -> ClaimDocument:
    row = ClaimDocumentRow(
        id=values["id"],
        claim_id=values["claim_id"],
        uploaded_file_id=values.get("uploaded_file_id"),
        document_type=values["document_type"],
        filename=values["filename"],
        extraction_status=values["extraction_status"],
        extracted_fields=values.get("extracted_fields", {}),
    )
    session.add(row)
    session.flush()
    return _document(row)


def fetch_documents(session: Session, claim_id: str) -> list[ClaimDocument]:
    rows = session.scalars(
        select(ClaimDocumentRow)
        .where(ClaimDocumentRow.claim_id == claim_id)
        .order_by(ClaimDocumentRow.created_at)
    )
    return [_document(row) for row in rows]


def insert_action(session: Session, values: dict[str, Any]) -> ProposedAction:
    row = ProposedActionRow(
        id=values["id"],
        claim_id=values["claim_id"],
        run_id=values.get("run_id"),
        action_type=values["action_type"],
        tool_server=values["tool_server"],
        tool_name=values["tool_name"],
        arguments=values.get("arguments", {}),
        reason=values["reason"],
        risk_level=values["risk_level"],
        status=values["status"],
        proposed_by=values["proposed_by"],
    )
    session.add(row)
    session.flush()
    return _action(row)


def fetch_actions(session: Session, claim_id: str) -> list[ProposedAction]:
    rows = session.scalars(
        select(ProposedActionRow)
        .where(ProposedActionRow.claim_id == claim_id)
        .order_by(ProposedActionRow.created_at.desc())
    )
    return [_action(row) for row in rows]


def fetch_action_for_owner(
    session: Session,
    action_id: str,
    claim_id: str,
    owner_user_id: str,
    *,
    for_update: bool = False,
) -> ProposedAction | None:
    stmt = (
        select(ProposedActionRow)
        .join(ClaimRow, ClaimRow.id == ProposedActionRow.claim_id)
        .where(
            ProposedActionRow.id == action_id,
            ProposedActionRow.claim_id == claim_id,
            ClaimRow.owner_user_id == owner_user_id,
        )
    )
    if for_update:
        stmt = stmt.with_for_update()
    row = session.scalar(stmt)
    return _action(row) if row else None


def record_action_decision(
    session: Session,
    action_id: str,
    actor_user_id: str,
    decision: str,
    comment: str | None,
) -> ProposedAction:
    session.add(
        ClaimActionApproval(
            proposed_action_id=action_id,
            actor_user_id=actor_user_id,
            decision=decision,
            comment=comment,
        )
    )
    approved = decision == "APPROVED"
    row = session.scalar(
        update(ProposedActionRow)
        .where(ProposedActionRow.id == action_id)
        .values(
            status=decision,
            approved_by=actor_user_id if approved else None,
            approved_at=func.now() if approved else None,
            updated_at=func.now(),
        )
        .returning(ProposedActionRow)
    )
    return _action(row)


def add_audit_event(
    session: Session,
    claim_id: str,
    actor_user_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    session.add(
        ClaimAuditEventRow(
            claim_id=claim_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            payload=payload,
        )
    )


def fetch_audit_events(
    session: Session, claim_id: str, *, limit: int = 50
) -> list[ClaimAuditEvent]:
    rows = session.scalars(
        select(ClaimAuditEventRow)
        .where(ClaimAuditEventRow.claim_id == claim_id)
        .order_by(ClaimAuditEventRow.created_at.desc())
        .limit(limit)
    )
    return [_audit_event(row) for row in rows]


def insert_review_run(
    session: Session,
    run_id: str,
    claim_id: str,
    owner_user_id: str,
    *,
    status: str = "QUEUED",
    current_step: str = "QUEUED",
) -> ClaimReviewRun:
    row = ClaimReviewRunRow(
        id=run_id,
        claim_id=claim_id,
        owner_user_id=owner_user_id,
        status=status,
        current_step=current_step,
    )
    session.add(row)
    session.flush()
    return _review_run(row)


def update_review_run(
    session: Session,
    run_id: str,
    *,
    status: str | None = None,
    current_step: str | None = None,
    result: dict[str, Any] | None = None,
    error: str | None = None,
    complete: bool = False,
) -> ClaimReviewRun:
    values: dict[str, Any] = {"error": error, "updated_at": func.now()}
    if status is not None:
        values["status"] = status
    if current_step is not None:
        values["current_step"] = current_step
    if result is not None:
        values["result"] = result
    if complete:
        values["completed_at"] = func.now()
    row = session.scalar(
        update(ClaimReviewRunRow)
        .where(ClaimReviewRunRow.id == run_id)
        .values(**values)
        .returning(ClaimReviewRunRow)
    )
    return _review_run(row)


def fetch_review_run_for_owner(
    session: Session,
    run_id: str,
    claim_id: str,
    owner_user_id: str,
) -> ClaimReviewRun | None:
    row = session.scalar(
        select(ClaimReviewRunRow).where(
            ClaimReviewRunRow.id == run_id,
            ClaimReviewRunRow.claim_id == claim_id,
            ClaimReviewRunRow.owner_user_id == owner_user_id,
        )
    )
    return _review_run(row) if row else None


def fetch_latest_review_run(
    session: Session,
    claim_id: str,
    owner_user_id: str,
) -> ClaimReviewRun | None:
    row = session.scalar(
        select(ClaimReviewRunRow)
        .where(
            ClaimReviewRunRow.claim_id == claim_id,
            ClaimReviewRunRow.owner_user_id == owner_user_id,
        )
        .order_by(ClaimReviewRunRow.created_at.desc())
        .limit(1)
    )
    return _review_run(row) if row else None
