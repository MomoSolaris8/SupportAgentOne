from fastapi import Depends, HTTPException

from supportagent.auth.dependencies import get_current_user
from supportagent.auth.schemas import AuthUser
from supportagent.claims.schemas import (
    ActionDecisionRequest,
    Claim,
    ClaimDetail,
    ClaimDocument,
    ClaimReviewResponse,
    ClaimsResponse,
    CreateClaimDocumentRequest,
    CreateClaimRequest,
    CreateProposedActionRequest,
    ProposedAction,
)
from supportagent.claims.review_workflow import review_claim
from supportagent.claims.service import (
    ClaimActionConflictError,
    ClaimNotFoundError,
    approve_action,
    create_claim,
    create_claim_document,
    create_proposed_action,
    get_claim,
    list_claims,
    reject_action,
)


def _not_found(error: ClaimNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(error))


def create_claim_route(
    request: CreateClaimRequest,
    user: AuthUser = Depends(get_current_user),
) -> Claim:
    return create_claim(user.id, request)


def list_claims_route(user: AuthUser = Depends(get_current_user)) -> ClaimsResponse:
    return ClaimsResponse(claims=list_claims(user.id))


def get_claim_route(
    claim_id: str,
    user: AuthUser = Depends(get_current_user),
) -> ClaimDetail:
    try:
        return get_claim(claim_id, user.id)
    except ClaimNotFoundError as error:
        raise _not_found(error) from error


def create_claim_document_route(
    claim_id: str,
    request: CreateClaimDocumentRequest,
    user: AuthUser = Depends(get_current_user),
) -> ClaimDocument:
    try:
        return create_claim_document(claim_id, user.id, request)
    except ClaimNotFoundError as error:
        raise _not_found(error) from error


def create_proposed_action_route(
    claim_id: str,
    request: CreateProposedActionRequest,
    user: AuthUser = Depends(get_current_user),
) -> ProposedAction:
    try:
        return create_proposed_action(claim_id, user.id, request)
    except ClaimNotFoundError as error:
        raise _not_found(error) from error


def review_claim_route(
    claim_id: str,
    user: AuthUser = Depends(get_current_user),
) -> ClaimReviewResponse:
    try:
        return review_claim(claim_id, user.id)
    except ClaimNotFoundError as error:
        raise _not_found(error) from error


def approve_action_route(
    claim_id: str,
    action_id: str,
    request: ActionDecisionRequest,
    user: AuthUser = Depends(get_current_user),
) -> ProposedAction:
    try:
        return approve_action(claim_id, action_id, user.id, request.comment)
    except ClaimNotFoundError as error:
        raise _not_found(error) from error
    except ClaimActionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def reject_action_route(
    claim_id: str,
    action_id: str,
    request: ActionDecisionRequest,
    user: AuthUser = Depends(get_current_user),
) -> ProposedAction:
    try:
        return reject_action(claim_id, action_id, user.id, request.comment)
    except ClaimNotFoundError as error:
        raise _not_found(error) from error
    except ClaimActionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
