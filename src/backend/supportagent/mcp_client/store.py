import json
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Any

import psycopg
import requests

from supportagent.rag.vector_store import get_connection


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


DEFAULT_SERVER_ROWS = [
    (
        "weather_mcp",
        "Local Google Weather MCP server",
        "stdio",
        json.dumps(
            {
                "command": "python",
                "args": ["-m", "supportagent.mcp_servers.weather_mcp", "--transport", "stdio"],
            }
        ),
        True,
    ),
    (
        "teams_mcp",
        "Local Microsoft Graph MCP server",
        "stdio",
        json.dumps(
            {
                "command": "python",
                "args": ["-m", "supportagent.mcp_servers.teams_mcp", "--transport", "stdio"],
            }
        ),
        True,
    ),
]

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
}

PERSONAL_ACCOUNT_DISABLED_TOOL_NAMES = {
    "batch_get_user_info",
    "list_chats",
    "create_message",
}

DEFAULT_TOOL_POLICIES = [
    ("weather_mcp", "get_weather"),
    ("teams_mcp", "get_my_profile"),
    ("teams_mcp", "batch_get_user_info"),
    ("teams_mcp", "create_calendar"),
    ("teams_mcp", "delete_calendar"),
    ("teams_mcp", "get_calendar_info"),
    ("teams_mcp", "get_calendars_list"),
    ("teams_mcp", "update_calendar"),
    ("teams_mcp", "create_calendar_event"),
    ("teams_mcp", "create_default_calendar_event"),
    ("teams_mcp", "append_calendar_event_attendee"),
    ("teams_mcp", "get_calendar_event"),
    ("teams_mcp", "update_calendar_event"),
    ("teams_mcp", "delete_calendar_event"),
    ("teams_mcp", "create_document"),
    ("teams_mcp", "get_document"),
    ("teams_mcp", "create_folder"),
    ("teams_mcp", "list_folder_files"),
    ("teams_mcp", "list_chats"),
    ("teams_mcp", "create_message"),
]


def create_mcp_schema(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mcp_servers (
            server_name TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            transport TEXT NOT NULL CHECK (transport IN ('stdio', 'sse', 'streamable_http')),
            config JSONB NOT NULL DEFAULT '{}'::jsonb,
            enabled BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mcp_tool_policies (
            server_name TEXT NOT NULL REFERENCES mcp_servers(server_name) ON DELETE CASCADE,
            tool_name TEXT NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT true,
            auto_allowed BOOLEAN NOT NULL DEFAULT false,
            requires_confirmation BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (server_name, tool_name)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mcp_user_credentials (
            user_id TEXT NOT NULL,
            server_name TEXT NOT NULL REFERENCES mcp_servers(server_name) ON DELETE CASCADE,
            credentials JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, server_name)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mcp_oauth_states (
            state TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mcp_tool_audit_logs (
            id BIGSERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            server_name TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('success', 'error', 'blocked')),
            arguments JSONB NOT NULL DEFAULT '{}'::jsonb,
            result_preview TEXT,
            error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS mcp_tool_audit_user_created_idx
        ON mcp_tool_audit_logs (user_id, created_at DESC)
        """
    )
    for server_name, display_name, transport, config, enabled in DEFAULT_SERVER_ROWS:
        conn.execute(
            """
            INSERT INTO mcp_servers (server_name, display_name, transport, config, enabled)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (server_name) DO NOTHING
            """,
            (server_name, display_name, transport, config, enabled),
        )
    for server_name, tool_name in DEFAULT_TOOL_POLICIES:
        is_read_only = tool_name in READ_ONLY_TOOL_NAMES
        is_enabled = tool_name not in PERSONAL_ACCOUNT_DISABLED_TOOL_NAMES
        conn.execute(
            """
            INSERT INTO mcp_tool_policies
                (server_name, tool_name, enabled, auto_allowed, requires_confirmation)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (server_name, tool_name)
            DO UPDATE SET
                enabled = EXCLUDED.enabled,
                auto_allowed = EXCLUDED.auto_allowed,
                requires_confirmation = EXCLUDED.requires_confirmation,
                updated_at = now()
            """,
            (server_name, tool_name, is_enabled, is_enabled and is_read_only, is_enabled and not is_read_only),
        )
    conn.commit()


def ensure_mcp_schema() -> None:
    conn = get_connection()
    try:
        create_mcp_schema(conn)
    finally:
        conn.close()


def list_mcp_servers() -> list[dict[str, Any]]:
    ensure_mcp_schema()
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT server_name, display_name, transport, config, enabled, updated_at
            FROM mcp_servers
            ORDER BY server_name
            """
        ).fetchall()
        return [
            {
                "server_name": row[0],
                "display_name": row[1],
                "transport": row[2],
                "config": row[3],
                "enabled": row[4],
                "updated_at": row[5].isoformat(),
            }
            for row in rows
        ]
    finally:
        conn.close()


def upsert_mcp_server(
    *,
    server_name: str,
    display_name: str,
    transport: str,
    config: dict[str, Any],
    enabled: bool,
) -> None:
    ensure_mcp_schema()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO mcp_servers (server_name, display_name, transport, config, enabled)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (server_name)
            DO UPDATE SET
                display_name = EXCLUDED.display_name,
                transport = EXCLUDED.transport,
                config = EXCLUDED.config,
                enabled = EXCLUDED.enabled,
                updated_at = now()
            """,
            (server_name, display_name, transport, json.dumps(config), enabled),
        )
        conn.commit()
    finally:
        conn.close()


def list_tool_policies() -> list[MCPToolPolicy]:
    ensure_mcp_schema()
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT server_name, tool_name, enabled, auto_allowed, requires_confirmation
            FROM mcp_tool_policies
            ORDER BY server_name, tool_name
            """
        ).fetchall()
        return [MCPToolPolicy(*row) for row in rows]
    finally:
        conn.close()


def get_tool_policy(server_name: str, tool_name: str) -> MCPToolPolicy:
    ensure_mcp_schema()
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT server_name, tool_name, enabled, auto_allowed, requires_confirmation
            FROM mcp_tool_policies
            WHERE server_name = %s AND tool_name = %s
            """,
            (server_name, tool_name),
        ).fetchone()
        if row:
            return MCPToolPolicy(*row)
        is_read_only = tool_name in READ_ONLY_TOOL_NAMES
        return MCPToolPolicy(
            server_name=server_name,
            tool_name=tool_name,
            enabled=True,
            auto_allowed=is_read_only,
            requires_confirmation=not is_read_only,
        )
    finally:
        conn.close()


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


def upsert_user_credentials(user_id: str, server_name: str, credentials: dict[str, Any]) -> None:
    ensure_mcp_schema()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO mcp_user_credentials (user_id, server_name, credentials)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, server_name)
            DO UPDATE SET credentials = EXCLUDED.credentials, updated_at = now()
            """,
            (user_id, server_name, json.dumps(credentials)),
        )
        conn.commit()
    finally:
        conn.close()


def save_oauth_state(state: str, user_id: str, provider: str, ttl_minutes: int = 10) -> None:
    ensure_mcp_schema()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO mcp_oauth_states (state, user_id, provider, expires_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (state)
            DO UPDATE SET user_id = EXCLUDED.user_id, provider = EXCLUDED.provider, expires_at = EXCLUDED.expires_at
            """,
            (state, user_id, provider, expires_at),
        )
        conn.commit()
    finally:
        conn.close()


def consume_oauth_state(state: str, provider: str) -> str | None:
    ensure_mcp_schema()
    conn = get_connection()
    try:
        row = conn.execute(
            """
            DELETE FROM mcp_oauth_states
            WHERE state = %s AND provider = %s AND expires_at > now()
            RETURNING user_id
            """,
            (state, provider),
        ).fetchone()
        conn.commit()
        return row[0] if row else None
    finally:
        conn.close()


def get_user_credentials(user_id: str | None, server_name: str) -> dict[str, Any]:
    if not user_id:
        return {}
    ensure_mcp_schema()
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT credentials
            FROM mcp_user_credentials
            WHERE user_id = %s AND server_name = %s
            """,
            (user_id, server_name),
        ).fetchone()
        return row[0] if row else {}
    finally:
        conn.close()


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
    ensure_mcp_schema()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO mcp_tool_audit_logs
                (user_id, server_name, tool_name, status, arguments, result_preview, error)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                server_name,
                tool_name,
                status,
                json.dumps(redact_arguments(arguments), ensure_ascii=False),
                result_preview,
                error,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_audit_logs(user_id: str, limit: int = 50) -> list[MCPAuditRecord]:
    ensure_mcp_schema()
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, user_id, server_name, tool_name, status, arguments,
                   result_preview, error, created_at
            FROM mcp_tool_audit_logs
            WHERE user_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (user_id, limit),
        ).fetchall()
        return [
            MCPAuditRecord(
                id=row[0],
                user_id=row[1],
                server_name=row[2],
                tool_name=row[3],
                status=row[4],
                arguments=row[5],
                result_preview=row[6],
                error=row[7],
                created_at=row[8].isoformat(),
            )
            for row in rows
        ]
    finally:
        conn.close()
