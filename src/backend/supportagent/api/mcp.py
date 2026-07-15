import json
from typing import Any

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from supportagent.auth.dependencies import get_current_user
from supportagent.auth.schemas import AuthUser
from supportagent.memory.service import record_mcp_action_turn
from supportagent.mcp_client.client import MultiServerMCPClient
from supportagent.mcp_client.config import local_mcp_configs
from supportagent.mcp_client.store import (
    add_audit_log,
    inject_user_credentials,
    list_audit_logs,
    list_mcp_servers,
    list_tool_policies,
    tool_manual_allowed,
    upsert_mcp_server,
    upsert_user_credentials,
)


class McpToolCallRequest(BaseModel):
    server: str
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False
    thread_id: str | None = None
    question: str | None = None


class McpToolsResponse(BaseModel):
    tools: list[dict[str, Any]]


class McpToolCallResponse(BaseModel):
    server: str
    tool: str
    result: Any


class McpServersResponse(BaseModel):
    servers: list[dict[str, Any]]
    policies: list[dict[str, Any]]


class McpCredentialRequest(BaseModel):
    server: str
    credentials: dict[str, Any] = Field(default_factory=dict)


class McpServerUpsertRequest(BaseModel):
    server_name: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=200)
    transport: str
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class McpAuditResponse(BaseModel):
    audit_logs: list[dict[str, Any]]


def _tool_parameters(input_schema: dict[str, Any] | None) -> list[dict[str, Any]]:
    schema = input_schema or {"type": "object", "properties": {}}
    required = set(schema.get("required", []))
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return []
    return [
        {
            "name": name,
            "type": property_schema.get("type", "unknown") if isinstance(property_schema, dict) else "unknown",
            "required": name in required,
            "default": property_schema.get("default") if isinstance(property_schema, dict) else None,
            "description": property_schema.get("description") if isinstance(property_schema, dict) else None,
        }
        for name, property_schema in properties.items()
    ]


async def mcp_tools(user: AuthUser = Depends(get_current_user)) -> McpToolsResponse:
    client = MultiServerMCPClient(local_mcp_configs())
    try:
        tools_by_server = await client.list_tools()
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Could not list MCP tools: {error}") from error

    tools = []
    for server_name, server_tools in tools_by_server.items():
        for tool in server_tools:
            input_schema = tool.inputSchema or {"type": "object", "properties": {}}
            example_arguments = {}
            for parameter in _tool_parameters(input_schema):
                if parameter["required"]:
                    example_arguments[parameter["name"]] = parameter["default"] or ""
            tools.append(
                {
                    "server": server_name,
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": _tool_parameters(input_schema),
                    "example_arguments": example_arguments,
                }
            )
    return McpToolsResponse(tools=tools)


def mcp_servers(user: AuthUser = Depends(get_current_user)) -> McpServersResponse:
    return McpServersResponse(
        servers=list_mcp_servers(),
        policies=[
            {
                "server_name": policy.server_name,
                "tool_name": policy.tool_name,
                "enabled": policy.enabled,
                "auto_allowed": policy.auto_allowed,
                "requires_confirmation": policy.requires_confirmation,
            }
            for policy in list_tool_policies()
        ],
    )


def mcp_server_upsert(
    request: McpServerUpsertRequest,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool]:
    if request.transport not in {"stdio", "sse", "streamable_http"}:
        raise HTTPException(status_code=400, detail="transport must be stdio, sse, or streamable_http.")
    if request.transport == "stdio" and not request.config.get("command"):
        raise HTTPException(status_code=400, detail="stdio MCP servers require config.command.")
    if request.transport in {"sse", "streamable_http"} and not request.config.get("url"):
        raise HTTPException(status_code=400, detail="remote MCP servers require config.url.")
    upsert_mcp_server(
        server_name=request.server_name,
        display_name=request.display_name,
        transport=request.transport,
        config=request.config,
        enabled=request.enabled,
    )
    return {"ok": True}


def mcp_credentials(
    request: McpCredentialRequest,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool]:
    upsert_user_credentials(user.id, request.server, request.credentials)
    return {"ok": True}


def mcp_audit(user: AuthUser = Depends(get_current_user)) -> McpAuditResponse:
    return McpAuditResponse(
        audit_logs=[
            {
                "id": record.id,
                "server_name": record.server_name,
                "tool_name": record.tool_name,
                "status": record.status,
                "arguments": record.arguments,
                "result_preview": record.result_preview,
                "error": record.error,
                "created_at": record.created_at,
            }
            for record in list_audit_logs(user.id)
        ]
    )


_NOISY_RESULT_KEYS = {
    "@odata.context",
    "@odata.etag",
    "id",
    "changeKey",
    "iCalUId",
    "uid",
    "transactionId",
    "categories",
    "hasAttachments",
    "reminderMinutesBeforeStart",
    "isReminderOn",
    "originalStartTimeZone",
    "originalEndTimeZone",
    "createdDateTime",
    "lastModifiedDateTime",
    "sensitivity",
    "showAs",
    "isAllDay",
    "isCancelled",
    "isOrganizer",
    "responseRequested",
    "seriesMasterId",
    "type",
    "allowNewTimeProposals",
    "isOnlineMeeting",
    "onlineMeetingProvider",
    "recurrence",
    "importance",
    "isDraft",
}
_PRIORITY_RESULT_KEYS = ("subject", "displayName", "name", "start", "end", "location", "webLink", "bodyPreview")


def _summarize_tool_result(result: str) -> str:
    """Turn a raw Microsoft Graph / MCP JSON response into a short, readable
    summary for chat history instead of dumping the entire payload."""
    try:
        parsed = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return result[:500]

    if not isinstance(parsed, dict):
        return json.dumps(parsed, ensure_ascii=False)[:500]

    highlights = {k: v for k, v in parsed.items() if k not in _NOISY_RESULT_KEYS and v not in (None, "", [], {})}
    if not highlights:
        return json.dumps(parsed, ensure_ascii=False)[:500]

    lines: list[str] = []
    for key in _PRIORITY_RESULT_KEYS:
        if key not in highlights:
            continue
        value = highlights.pop(key)
        if isinstance(value, dict):
            value = value.get("dateTime") or value.get("displayName")
            if not value:
                continue
        lines.append(f"- {key}: {value}")
    for key, value in list(highlights.items())[:5]:
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


async def mcp_call(
    request: McpToolCallRequest,
    user: AuthUser = Depends(get_current_user),
) -> McpToolCallResponse:
    allowed, block_reason = tool_manual_allowed(request.server, request.tool, request.confirmed)
    if not allowed:
        add_audit_log(
            user_id=user.id,
            server_name=request.server,
            tool_name=request.tool,
            status="blocked",
            arguments=request.arguments,
            error=block_reason,
        )
        raise HTTPException(status_code=403, detail=block_reason)

    arguments = inject_user_credentials(user.id, request.server, request.arguments)
    client = MultiServerMCPClient(local_mcp_configs([request.server]))
    try:
        result = await client.call_tool(request.server, request.tool, arguments)
    except Exception as error:
        add_audit_log(
            user_id=user.id,
            server_name=request.server,
            tool_name=request.tool,
            status="error",
            arguments=arguments,
            error=str(error),
        )
        raise HTTPException(status_code=400, detail=f"MCP tool call failed: {error}") from error

    add_audit_log(
        user_id=user.id,
        server_name=request.server,
        tool_name=request.tool,
        status="success",
        arguments=arguments,
        result_preview=str(result)[:500],
    )
    record_mcp_action_turn(
        thread_id=request.thread_id,
        user_id=user.id,
        question=request.question or f"[MCP-Aktion] {request.server}.{request.tool}",
        summary=f"MCP-Aktion ausgefuehrt: {request.server}.{request.tool}\n\n{_summarize_tool_result(result)}",
    )
    return McpToolCallResponse(server=request.server, tool=request.tool, result=result)
