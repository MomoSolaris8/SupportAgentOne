from typing import Any, Literal

from pydantic import BaseModel, Field


ClaimStatus = Literal[
    "DRAFT",
    "DOCUMENTS_PENDING",
    "READY_FOR_REVIEW",
    "UNDER_REVIEW",
    "NEEDS_INFORMATION",
    "APPROVED",
    "REJECTED",
    "CLOSED",
]

ProductLine = Literal[
    "unknown",
    "household",
    "residential_building",
    "vehicle",
    "liability",
    "legal_expense",
]

ActionType = Literal[
    "CREATE_JIRA_ISSUE",
    "SEND_TEAMS_NOTIFICATION",
    "UPDATE_CLAIM_STATUS",
]

ActionStatus = Literal[
    "PROPOSED",
    "WAITING_FOR_APPROVAL",
    "APPROVED",
    "REJECTED",
    "EXECUTING",
    "SUCCEEDED",
    "FAILED",
    "VERIFICATION_FAILED",
]


class Claim(BaseModel):
    id: str
    owner_user_id: str
    policy_id: str
    product_line: ProductLine
    policy_version: str | None = None
    jurisdiction: str
    customer_reference: str
    claim_type: str
    incident_date: str | None = None
    status: ClaimStatus
    created_at: str
    updated_at: str


class ClaimDocument(BaseModel):
    id: str
    claim_id: str
    uploaded_file_id: str | None = None
    document_type: str
    filename: str
    extraction_status: str
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ProposedAction(BaseModel):
    id: str
    claim_id: str
    run_id: str | None = None
    action_type: ActionType
    tool_server: str
    tool_name: str
    arguments: dict[str, Any]
    reason: str
    risk_level: Literal["medium", "high"]
    status: ActionStatus
    proposed_by: str
    approved_by: str | None = None
    approved_at: str | None = None
    created_at: str
    updated_at: str


class CreateClaimRequest(BaseModel):
    policy_id: str = Field(min_length=1, max_length=120)
    product_line: ProductLine
    policy_version: str | None = Field(default=None, max_length=80)
    jurisdiction: str = Field(default="DE", min_length=2, max_length=20)
    customer_reference: str = Field(min_length=1, max_length=120)
    claim_type: str = Field(min_length=1, max_length=120)
    incident_date: str | None = Field(default=None, max_length=40)


class CreateClaimDocumentRequest(BaseModel):
    uploaded_file_id: str | None = Field(default=None, max_length=120)
    document_type: str = Field(min_length=1, max_length=120)
    filename: str = Field(min_length=1, max_length=255)
    extraction_status: str = Field(default="PENDING", max_length=40)
    extracted_fields: dict[str, Any] = Field(default_factory=dict)


class CreateProposedActionRequest(BaseModel):
    run_id: str | None = Field(default=None, max_length=120)
    action_type: ActionType
    tool_server: str = Field(min_length=1, max_length=120)
    tool_name: str = Field(min_length=1, max_length=120)
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(min_length=1, max_length=2000)


class ActionDecisionRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=1000)


class ClaimDetail(BaseModel):
    claim: Claim
    documents: list[ClaimDocument] = Field(default_factory=list)
    proposed_actions: list[ProposedAction] = Field(default_factory=list)


class ClaimsResponse(BaseModel):
    claims: list[Claim] = Field(default_factory=list)


class ClaimEvidence(BaseModel):
    source_id: str
    title: str
    url: str
    source: str


class ClaimReviewResponse(BaseModel):
    run_id: str
    claim_id: str
    required_documents: list[str]
    present_documents: list[str]
    missing_documents: list[str]
    optional_documents: list[str]
    conditional_documents: list[str]
    document_requirements: list[dict[str, Any]] = Field(default_factory=list)
    evidence_status: Literal["sufficient", "insufficient"]
    evidence_reason: str
    evidence: list[ClaimEvidence] = Field(default_factory=list)
    recommendation: str
    proposed_action: ProposedAction | None = None
