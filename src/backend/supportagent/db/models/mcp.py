from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from supportagent.db.base import Base


class McpServer(Base):
    __tablename__ = "mcp_servers"
    __table_args__ = (
        CheckConstraint(
            "transport IN ('stdio', 'sse', 'streamable_http')",
            name="mcp_servers_transport_check",
        ),
    )

    server_name: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text)
    transport: Mapped[str] = mapped_column(Text)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class McpToolPolicy(Base):
    __tablename__ = "mcp_tool_policies"

    server_name: Mapped[str] = mapped_column(
        Text,
        ForeignKey("mcp_servers.server_name", ondelete="CASCADE"),
        primary_key=True,
    )
    tool_name: Mapped[str] = mapped_column(Text, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    auto_allowed: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    requires_confirmation: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class McpUserCredential(Base):
    __tablename__ = "mcp_user_credentials"

    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    server_name: Mapped[str] = mapped_column(
        Text,
        ForeignKey("mcp_servers.server_name", ondelete="CASCADE"),
        primary_key=True,
    )
    credentials: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class McpOAuthState(Base):
    __tablename__ = "mcp_oauth_states"

    state: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))


class McpToolAuditLog(Base):
    __tablename__ = "mcp_tool_audit_logs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'error', 'blocked')",
            name="mcp_tool_audit_logs_status_check",
        ),
        Index("mcp_tool_audit_user_created_idx", "user_id", text("created_at DESC")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    server_name: Mapped[str] = mapped_column(Text)
    tool_name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    arguments: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    result_preview: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class McpIdempotencyRecord(Base):
    __tablename__ = "mcp_idempotency_records"
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'succeeded')",
            name="mcp_idempotency_records_status_check",
        ),
    )

    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    server_name: Mapped[str] = mapped_column(Text, primary_key=True)
    tool_name: Mapped[str] = mapped_column(Text, primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(Text, primary_key=True)
    status: Mapped[str] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
