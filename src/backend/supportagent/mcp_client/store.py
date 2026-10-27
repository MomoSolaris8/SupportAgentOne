from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert

from supportagent.db.models import (
    McpIdempotencyRecord,
    McpOAuthState,
    McpServer,
    McpToolAuditLog,
    McpUserCredential,
)
from supportagent.db.models import McpToolPolicy as ToolPolicyRow
from supportagent.db.session import SessionLocal


@dataclass(frozen=True)
class MCPToolPolicy:
    server_name: str
    tool_name: str
    enabled: bool
    auto_allowed: bool
    requires_confirmation: bool


@dataclass(frozen=True)
class MCPAuditRecord:
    id: int
    user_id: str
    server_name: str
    tool_name: str
    status: str
    arguments: dict[str, Any]
    result_preview: str | None
    error: str | None
    created_at: str


@dataclass(frozen=True)
class MCPIdempotencyClaim:
    status: str
    result: str | None = None


READ_ONLY_TOOL_NAMES = {
    "get_my_profile",
    "batch_get_user_info",
    "get_calendar_info",
    "get_calendars_list",
    "get_calendar_event",
    "get_document",
    "list_folder_files",
    "list_chats",
    "get_weather",
    "get_current_time",
}


def list_mcp_servers() -> list[dict[str, Any]]:
    with SessionLocal() as session:
        servers = session.scalars(select(McpServer).order_by(McpServer.server_name))
        return [
            {
                "server_name": server.server_name,
                "display_name": server.display_name,
                "transport": server.transport,
                "config": server.config,
                "enabled": server.enabled,
                "updated_at": server.updated_at.isoformat(),
            }
            for server in servers
        ]


def upsert_mcp_server(
    *,
    server_name: str,
    display_name: str,
    transport: str,
    config: dict[str, Any],
    enabled: bool,
) -> None:
    stmt = insert(McpServer).values(
        server_name=server_name,
        display_name=display_name,
        transport=transport,
        config=config,
        enabled=enabled,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[McpServer.server_name],
        set_={
            "display_name": stmt.excluded.display_name,
            "transport": stmt.excluded.transport,
            "config": stmt.excluded.config,
            "enabled": stmt.excluded.enabled,
            "updated_at": func.now(),
        },
    )
    with SessionLocal.begin() as session:
        session.execute(stmt)


def list_tool_policies() -> list[MCPToolPolicy]:
    with SessionLocal() as session:
        rows = session.execute(
            select(
                ToolPolicyRow.server_name,
                ToolPolicyRow.tool_name,
                ToolPolicyRow.enabled,
                ToolPolicyRow.auto_allowed,
                ToolPolicyRow.requires_confirmation,
            ).order_by(ToolPolicyRow.server_name, ToolPolicyRow.tool_name)
        )
        return [MCPToolPolicy(*row) for row in rows]


def get_tool_policy(server_name: str, tool_name: str) -> MCPToolPolicy:
    with SessionLocal() as session:
        row = session.get(ToolPolicyRow, (server_name, tool_name))
    if row:
        return MCPToolPolicy(
            server_name=row.server_name,
            tool_name=row.tool_name,
            enabled=row.enabled,
            auto_allowed=row.auto_allowed,
            requires_confirmation=row.requires_confirmation,
        )
    is_read_only = tool_name in READ_ONLY_TOOL_NAMES
    return MCPToolPolicy(
        server_name=server_name,
        tool_name=tool_name,
        enabled=True,
        auto_allowed=is_read_only,
        requires_confirmation=not is_read_only,
    )


def tool_auto_allowed(server_name: str, tool_name: str) -> bool:
    policy = get_tool_policy(server_name, tool_name)
    return policy.enabled and policy.auto_allowed and not policy.requires_confirmation


def tool_manual_allowed(server_name: str, tool_name: str, confirmed: bool) -> tuple[bool, str | None]:
    policy = get_tool_policy(server_name, tool_name)
    if not policy.enabled:
        return False, "Tool is disabled by policy."
    if policy.requires_confirmation and not confirmed:
        return False, "Tool requires explicit confirmation."
    return True, None


def _idempotency_key_matches(
    user_id: str, server_name: str, tool_name: str, idempotency_key: str
):
    return and_(
        McpIdempotencyRecord.user_id == user_id,
        McpIdempotencyRecord.server_name == server_name,
        McpIdempotencyRecord.tool_name == tool_name,
        McpIdempotencyRecord.idempotency_key == idempotency_key,
    )


def claim_idempotency_key(
    *,
    user_id: str,
    server_name: str,
    tool_name: str,
    idempotency_key: str,
) -> MCPIdempotencyClaim:
    """Atomically reserve a write action or replay its earlier successful result."""
    with SessionLocal.begin() as session:
        inserted = session.scalar(
            insert(McpIdempotencyRecord)
            .values(
                user_id=user_id,
                server_name=server_name,
                tool_name=tool_name,
                idempotency_key=idempotency_key,
                status="in_progress",
            )
            .on_conflict_do_nothing()
            .returning(McpIdempotencyRecord.status)
        )
        if inserted:
            return MCPIdempotencyClaim(status="execute")

        row = session.execute(
            select(McpIdempotencyRecord.status, McpIdempotencyRecord.result).where(
                _idempotency_key_matches(user_id, server_name, tool_name, idempotency_key)
            )
        ).first()
    if row and row.status == "succeeded":
        return MCPIdempotencyClaim(status="replay", result=row.result)
    return MCPIdempotencyClaim(status="in_progress")


def complete_idempotency_key(
    *,
    user_id: str,
    server_name: str,
    tool_name: str,
    idempotency_key: str,
    result: str,
) -> None:
    with SessionLocal.begin() as session:
        session.execute(
            update(McpIdempotencyRecord)
            .where(_idempotency_key_matches(user_id, server_name, tool_name, idempotency_key))
            .values(status="succeeded", result=result, updated_at=func.now())
        )


def abandon_idempotency_key(
    *,
    user_id: str,
    server_name: str,
    tool_name: str,
    idempotency_key: str,
) -> None:
    with SessionLocal.begin() as session:
        session.execute(
            delete(McpIdempotencyRecord).where(
                _idempotency_key_matches(user_id, server_name, tool_name, idempotency_key),
                McpIdempotencyRecord.status == "in_progress",
            )
        )


def upsert_user_credentials(user_id: str, server_name: str, credentials: dict[str, Any]) -> None:
    stmt = insert(McpUserCredential).values(
        user_id=user_id, server_name=server_name, credentials=credentials
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[McpUserCredential.user_id, McpUserCredential.server_name],
        set_={"credentials": stmt.excluded.credentials, "updated_at": func.now()},
    )
    with SessionLocal.begin() as session:
        session.execute(stmt)


def save_oauth_state(state: str, user_id: str, provider: str, ttl_minutes: int = 10) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    stmt = insert(McpOAuthState).values(
        state=state, user_id=user_id, provider=provider, expires_at=expires_at
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[McpOAuthState.state],
        set_={
            "user_id": stmt.excluded.user_id,
            "provider": stmt.excluded.provider,
            "expires_at": stmt.excluded.expires_at,
        },
    )
    with SessionLocal.begin() as session:
        session.execute(stmt)


def consume_oauth_state(state: str, provider: str) -> str | None:
    with SessionLocal.begin() as session:
        return session.scalar(
            delete(McpOAuthState)
            .where(
                McpOAuthState.state == state,
                McpOAuthState.provider == provider,
                McpOAuthState.expires_at > func.now(),
            )
            .returning(McpOAuthState.user_id)
        )


def get_user_credentials(user_id: str | None, server_name: str) -> dict[str, Any]:
    if not user_id:
        return {}
    with SessionLocal() as session:
        credentials = session.scalar(
            select(McpUserCredential.credentials).where(
                McpUserCredential.user_id == user_id,
                McpUserCredential.server_name == server_name,
            )
        )
    return credentials or {}


def inject_user_credentials(
    user_id: str | None,
    server_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    credentials = get_user_credentials(user_id, server_name)
    if not credentials:
        return arguments
    if server_name == "teams_mcp":
        credentials = refresh_microsoft_credentials_if_needed(user_id, server_name, credentials)
    merged = dict(arguments)
    for key in ("access_token", "api_key"):
        if key in credentials and key not in merged:
            merged[key] = credentials[key]
    return merged


def refresh_microsoft_credentials_if_needed(
    user_id: str | None,
    server_name: str,
    credentials: dict[str, Any],
) -> dict[str, Any]:
    if not user_id or "refresh_token" not in credentials:
        return credentials
    expires_at = credentials.get("expires_at")
    if isinstance(expires_at, str):
        try:
            expires = datetime.fromisoformat(expires_at)
        except ValueError:
            expires = datetime.now(timezone.utc)
    else:
        expires = datetime.now(timezone.utc)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires > datetime.now(timezone.utc) + timedelta(minutes=5):
        return credentials

    import os

    client_id = os.environ.get("MICROSOFT_CLIENT_ID")
    client_secret = os.environ.get("MICROSOFT_CLIENT_SECRET")
    tenant = os.environ.get("MICROSOFT_TENANT", "consumers")
    scopes = os.environ.get(
        "MICROSOFT_SCOPES",
        "offline_access User.Read Calendars.ReadWrite Files.ReadWrite",
    )
    if not client_id:
        return credentials

    data = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": credentials["refresh_token"],
        "scope": scopes,
    }
    if client_secret:
        data["client_secret"] = client_secret
    response = requests.post(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data=data,
        timeout=20,
    )
    if response.status_code >= 400:
        return credentials
    payload = response.json()
    refreshed = {
        **credentials,
        "access_token": payload["access_token"],
        "refresh_token": payload.get("refresh_token", credentials["refresh_token"]),
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(seconds=int(payload.get("expires_in", 3600)))
        ).isoformat(),
        "scope": payload.get("scope", credentials.get("scope")),
    }
    upsert_user_credentials(user_id, server_name, refreshed)
    return refreshed


def redact_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(arguments)
    for key in ("access_token", "api_key", "token", "password", "client_secret"):
        if key in redacted:
            redacted[key] = "***"
    return redacted


def add_audit_log(
    user_id: str,
    server_name: str,
    tool_name: str,
    status: str,
    arguments: dict[str, Any],
    result_preview: str | None = None,
    error: str | None = None,
) -> None:
    with SessionLocal.begin() as session:
        session.add(
            McpToolAuditLog(
                user_id=user_id,
                server_name=server_name,
                tool_name=tool_name,
                status=status,
                arguments=redact_arguments(arguments),
                result_preview=result_preview,
                error=error,
            )
        )


def list_audit_logs(user_id: str, limit: int = 50) -> list[MCPAuditRecord]:
    with SessionLocal() as session:
        logs = session.scalars(
            select(McpToolAuditLog)
            .where(McpToolAuditLog.user_id == user_id)
            .order_by(McpToolAuditLog.created_at.desc(), McpToolAuditLog.id.desc())
            .limit(limit)
        )
        return [
            MCPAuditRecord(
                id=log.id,
                user_id=log.user_id,
                server_name=log.server_name,
                tool_name=log.tool_name,
                status=log.status,
                arguments=log.arguments,
                result_preview=log.result_preview,
                error=log.error,
                created_at=log.created_at.isoformat(),
            )
            for log in logs
        ]
