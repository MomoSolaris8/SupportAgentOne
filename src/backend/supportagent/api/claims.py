from fastapi import BackgroundTasks, Depends, HTTPException

from supportagent.auth.dependencies import get_current_user
from supportagent.auth.schemas import AuthUser
from supportagent.claims.schemas import (
    ActionDecisionRequest,
    Claim,
    ClaimDecisionRequest,
    ClaimDetail,
    ClaimDocument,
    ClaimNextStepRequest,
    ClaimReviewRun,
    ClaimSubmissionResponse,
    ClaimsResponse,
    CreateClaimDocumentRequest,
    CreateClaimRequest,
    CreateProposedActionRequest,
    ProposedAction,
)
from supportagent.claims.review_workflow import execute_claim_review_run
from supportagent.claims.service import (
    ClaimActionConflictError,
    ClaimNotFoundError,
    ClaimStateConflictError,
    apply_claim_next_step,
    apply_human_claim_decision,
    approve_action,
    create_claim,
    create_claim_document,
    create_proposed_action,
    get_claim,
    get_claim_review_run,
    list_claims,
    reject_action,
    start_claim_review_run,
    submit_claim_for_review,
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
    background_tasks: BackgroundTasks,
    user: AuthUser = Depends(get_current_user),
) -> ClaimReviewRun:
    try:
        run = start_claim_review_run(claim_id, user.id)
        background_tasks.add_task(execute_claim_review_run, claim_id, run.id, user.id)
        return run
    except ClaimNotFoundError as error:
        raise _not_found(error) from error
    except ClaimStateConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def submit_claim_route(
    claim_id: str,
    user: AuthUser = Depends(get_current_user),
) -> ClaimSubmissionResponse:
    try:
        return submit_claim_for_review(claim_id, user.id)
    except ClaimNotFoundError as error:
        raise _not_found(error) from error
    except ClaimStateConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def claim_review_run_route(
    claim_id: str,
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> ClaimReviewRun:
    try:
        return get_claim_review_run(claim_id, run_id, user.id)
    except ClaimNotFoundError as error:
        raise _not_found(error) from error


def claim_next_step_route(
    claim_id: str,
    request: ClaimNextStepRequest,
    user: AuthUser = Depends(get_current_user),
) -> Claim:
    try:
        return apply_claim_next_step(claim_id, user.id, request)
    except ClaimNotFoundError as error:
        raise _not_found(error) from error
    except ClaimStateConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def claim_decision_route(
    claim_id: str,
    request: ClaimDecisionRequest,
    user: AuthUser = Depends(get_current_user),
) -> Claim:
    try:
        return apply_human_claim_decision(claim_id, user.id, request)
    except ClaimNotFoundError as error:
        raise _not_found(error) from error
    except ClaimStateConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


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
