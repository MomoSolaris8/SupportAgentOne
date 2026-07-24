import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from supportagent.llm import complete_chat
from supportagent.mcp_client.client import MultiServerMCPClient
from supportagent.mcp_client.config import (
    dynamic_mcp_enabled,
    local_mcp_configs,
)
from supportagent.mcp_client.store import (
    add_audit_log,
    inject_user_credentials,
    tool_auto_allowed,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MCPToolCallTrace:
    server: str
    tool: str
    arguments: dict[str, Any]
    result_preview: str


@dataclass(frozen=True)
class MCPAgentResult:
    answer: str | None
    tool_calls: list[MCPToolCallTrace] = field(default_factory=list)
    error: str | None = None


def _openai_tool_name(server: str, tool: str) -> str:
    return f"{server}__{tool}"


def _decode_openai_tool_name(name: str) -> tuple[str, str]:
    server, tool = name.split("__", 1)
    return server, tool


def _tool_schema(server: str, tool: Any) -> dict[str, Any] | None:
    if not tool_auto_allowed(server, tool.name):
        return None
    schema = tool.inputSchema or {"type": "object", "properties": {}}
    properties = dict(schema.get("properties", {}))
    # These are injected from server env/per-user config, not selected by the model.
    properties.pop("access_token", None)
    properties.pop("api_key", None)
    required = [
        item
        for item in schema.get("required", [])
        if item not in {"access_token", "api_key"}
    ]
    return {
        "type": "function",
        "function": {
            "name": _openai_tool_name(server, tool.name),
            "description": f"[{server}] {tool.description or ''}",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


async def run_dynamic_mcp_agent(
    question: str,
    user_id: str | None = None,
    enabled_mcp_servers: list[str] | None = None,
    model: str | None = None,
) -> MCPAgentResult:
    if not dynamic_mcp_enabled():
        return MCPAgentResult(answer=None)
    if not enabled_mcp_servers:
        return MCPAgentResult(answer=None)

    configs = local_mcp_configs(enabled_mcp_servers)
    if not configs:
        return MCPAgentResult(answer=None)

    client = MultiServerMCPClient(configs)
    try:
        tools_by_server = await client.list_tools()
    except Exception as error:
        logger.exception("mcp_list_tools_failed")
        return MCPAgentResult(answer=None, error=str(error))

    openai_tools = []
    for server_name, server_tools in tools_by_server.items():
        for tool in server_tools:
            schema = _tool_schema(server_name, tool)
            if schema is not None:
                openai_tools.append(schema)

    if not openai_tools:
        return MCPAgentResult(answer=None)

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a tool-routing sub-agent. Use the available MCP tools only when the "
                "user's request clearly needs live external data or an action. If no tool is "
                "needed, answer with the exact text: NO_TOOL_NEEDED. Do not call write/action "
                "tools unless they are available in the tool list."
            ),
        },
        {"role": "user", "content": question},
    ]

    try:
        first = complete_chat(
            messages,
            requested_model=model,
            task="tool",
            tools=openai_tools,
            tool_choice="auto",
            temperature=0,
        )
    except Exception as error:
        logger.exception("mcp_tool_choice_failed")
        return MCPAgentResult(answer=None, error=str(error))

    tool_calls = first.tool_calls
    if not tool_calls:
        content = first.content.strip()
        if content == "NO_TOOL_NEEDED":
            return MCPAgentResult(answer=None)
        return MCPAgentResult(answer=content or None)

    messages.append(
        {
            "role": "assistant",
            "content": first.content,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                }
                for tool_call in tool_calls
            ],
        }
    )
    traces: list[MCPToolCallTrace] = []
    for tool_call in tool_calls:
        server_name, tool_name = _decode_openai_tool_name(tool_call.name)
        arguments = tool_call.arguments

        arguments_with_credentials = inject_user_credentials(user_id, server_name, arguments)
        try:
            tool_result = await client.call_tool(server_name, tool_name, arguments_with_credentials)
            if user_id:
                add_audit_log(
                    user_id=user_id,
                    server_name=server_name,
                    tool_name=tool_name,
                    status="success",
                    arguments=arguments_with_credentials,
                    result_preview=tool_result[:500],
                )
        except Exception as error:
            tool_result = f"Tool error: {error}"
            if user_id:
                add_audit_log(
                    user_id=user_id,
                    server_name=server_name,
                    tool_name=tool_name,
                    status="error",
                    arguments=arguments_with_credentials,
                    error=str(error),
                )

        traces.append(
            MCPToolCallTrace(
                server=server_name,
                tool=tool_name,
                arguments=arguments,
                result_preview=tool_result[:500],
            )
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result,
            }
        )

    final = complete_chat(
        messages
        + [
            {
                "role": "user",
                "content": "Use the MCP tool results above to answer the original request concisely.",
            }
        ],
        requested_model=model,
        task="tool",
        temperature=0,
    )
    return MCPAgentResult(answer=final.content, tool_calls=traces)


def run_dynamic_mcp_agent_sync(
    question: str,
    user_id: str | None = None,
    enabled_mcp_servers: list[str] | None = None,
    model: str | None = None,
) -> MCPAgentResult:
    try:
        return asyncio.run(
            run_dynamic_mcp_agent(
                question,
                user_id=user_id,
                enabled_mcp_servers=enabled_mcp_servers,
                model=model,
            )
        )
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                run_dynamic_mcp_agent(
                    question,
                    user_id=user_id,
                    enabled_mcp_servers=enabled_mcp_servers,
                    model=model,
                )
            )
        finally:
            loop.close()
