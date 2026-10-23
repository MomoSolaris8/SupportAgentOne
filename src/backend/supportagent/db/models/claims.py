from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from supportagent.db.base import Base


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (
        Index("claims_owner_updated_idx", "owner_user_id", text("updated_at DESC")),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(Text)
    policy_id: Mapped[str] = mapped_column(Text)
    product_line: Mapped[str] = mapped_column(Text, server_default="unknown")
    policy_version: Mapped[str | None] = mapped_column(Text)
    jurisdiction: Mapped[str] = mapped_column(Text, server_default="DE")
    customer_reference: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str] = mapped_column(Text)
    incident_date: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class ClaimDocument(Base):
    __tablename__ = "claim_documents"
    __table_args__ = (Index("claim_documents_claim_idx", "claim_id", "created_at"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        Text, ForeignKey("claims.id", ondelete="CASCADE")
    )
    uploaded_file_id: Mapped[str | None] = mapped_column(Text)
    document_type: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(Text)
    extraction_status: Mapped[str] = mapped_column(Text, server_default="PENDING")
    extracted_fields: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class ClaimAuditEvent(Base):
    __tablename__ = "claim_audit_events"
    __table_args__ = (Index("claim_audit_claim_idx", "claim_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        Text, ForeignKey("claims.id", ondelete="CASCADE")
    )
    actor_user_id: Mapped[str] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class ClaimReviewRun(Base):
    __tablename__ = "claim_review_runs"
    __table_args__ = (
        Index("claim_review_runs_claim_idx", "claim_id", text("created_at DESC")),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        Text, ForeignKey("claims.id", ondelete="CASCADE")
    )
    owner_user_id: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    current_step: Mapped[str] = mapped_column(Text)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class ProposedAction(Base):
    __tablename__ = "proposed_actions"
    __table_args__ = (
        Index("proposed_actions_claim_idx", "claim_id", text("created_at DESC")),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        Text, ForeignKey("claims.id", ondelete="CASCADE")
    )
    run_id: Mapped[str | None] = mapped_column(Text)
    action_type: Mapped[str] = mapped_column(Text)
    tool_server: Mapped[str] = mapped_column(Text)
    tool_name: Mapped[str] = mapped_column(Text)
    arguments: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    reason: Mapped[str] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    proposed_by: Mapped[str] = mapped_column(Text)
    approved_by: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class ClaimActionApproval(Base):
    __tablename__ = "claim_action_approvals"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('APPROVED', 'REJECTED')",
            name="claim_action_approvals_decision_check",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    proposed_action_id: Mapped[str] = mapped_column(
        Text, ForeignKey("proposed_actions.id", ondelete="CASCADE")
    )
    actor_user_id: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
