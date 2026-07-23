from typing import Any
from uuid import uuid4

from supportagent.claims.schemas import (
    Claim,
    ClaimDetail,
    ClaimDocument,
    CreateClaimDocumentRequest,
    CreateClaimRequest,
    CreateProposedActionRequest,
    ProposedAction,
)
from supportagent.claims.state_machine import action_risk_level, initial_action_status, validate_action_decision
from supportagent.claims.store import (
    add_audit_event,
    fetch_action_for_owner,
    fetch_actions,
    fetch_claim,
    fetch_claims,
    fetch_documents,
    insert_action,
    insert_claim,
    insert_document,
    record_action_decision,
)
from supportagent.rag.vector_store import get_connection


class ClaimNotFoundError(LookupError):
    pass


class ClaimActionConflictError(ValueError):
    pass


def create_claim(owner_user_id: str, request: CreateClaimRequest) -> Claim:
    conn = get_connection()
    try:
        claim = insert_claim(
            conn,
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
        add_audit_event(conn, claim.id, owner_user_id, "CLAIM_CREATED", {"status": claim.status})
        conn.commit()
        return claim
    finally:
        conn.close()


def list_claims(owner_user_id: str) -> list[Claim]:
    conn = get_connection()
    try:
        return fetch_claims(conn, owner_user_id)
    finally:
        conn.close()


def get_claim(claim_id: str, owner_user_id: str) -> ClaimDetail:
    conn = get_connection()
    try:
        claim = fetch_claim(conn, claim_id, owner_user_id)
        if claim is None:
            raise ClaimNotFoundError("Claim not found.")
        return ClaimDetail(
            claim=claim,
            documents=fetch_documents(conn, claim_id),
            proposed_actions=fetch_actions(conn, claim_id),
        )
    finally:
        conn.close()


def create_claim_document(
    claim_id: str, owner_user_id: str, request: CreateClaimDocumentRequest
) -> ClaimDocument:
    conn = get_connection()
    try:
        if fetch_claim(conn, claim_id, owner_user_id) is None:
            raise ClaimNotFoundError("Claim not found.")
        document = insert_document(
            conn,
            {
                "id": str(uuid4()),
                "claim_id": claim_id,
                **request.model_dump(),
            },
        )
        add_audit_event(
            conn, claim_id, owner_user_id, "CLAIM_DOCUMENT_REGISTERED",
            {"document_id": document.id, "document_type": document.document_type},
        )
        conn.commit()
        return document
    finally:
        conn.close()


def create_proposed_action(
    claim_id: str, owner_user_id: str, request: CreateProposedActionRequest
) -> ProposedAction:
    conn = get_connection()
    try:
        if fetch_claim(conn, claim_id, owner_user_id) is None:
            raise ClaimNotFoundError("Claim not found.")
        action = insert_action(
            conn,
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
            conn, claim_id, owner_user_id, "ACTION_PROPOSED",
            {"action_id": action.id, "action_type": action.action_type, "risk_level": action.risk_level},
        )
        conn.commit()
        return action
    finally:
        conn.close()


def _decide_action(
    claim_id: str, action_id: str, owner_user_id: str, decision: str, comment: str | None
) -> ProposedAction:
    conn = get_connection()
    try:
        action = fetch_action_for_owner(conn, action_id, claim_id, owner_user_id, for_update=True)
        if action is None:
            raise ClaimNotFoundError("Proposed action not found.")
        try:
            next_status = validate_action_decision(action.status, decision)
        except ValueError as error:
            raise ClaimActionConflictError(str(error)) from error
        updated = record_action_decision(conn, action_id, owner_user_id, next_status, comment)
        add_audit_event(
            conn, claim_id, owner_user_id, f"ACTION_{next_status}",
            {"action_id": action_id, "comment": comment},
        )
        conn.commit()
        return updated
    finally:
        conn.close()


def approve_action(
    claim_id: str, action_id: str, owner_user_id: str, comment: str | None = None
) -> ProposedAction:
    return _decide_action(claim_id, action_id, owner_user_id, "approve", comment)


def reject_action(
    claim_id: str, action_id: str, owner_user_id: str, comment: str | None = None
) -> ProposedAction:
    return _decide_action(claim_id, action_id, owner_user_id, "reject", comment)
