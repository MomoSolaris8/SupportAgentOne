import json
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any, AsyncIterator

from langchain_core.tools import StructuredTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, TextContent, Tool

from supportagent.mcp_client.config import MCPServerConfig


@asynccontextmanager
async def create_mcp_session(config: MCPServerConfig) -> AsyncIterator[ClientSession]:
    if config.transport == "stdio":
        if not config.command:
            raise ValueError(f"MCP server {config.server_name} is missing command.")
        params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env,
            cwd=config.cwd,
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                yield session
        return

    if not config.url:
        raise ValueError(f"MCP server {config.server_name} is missing url.")

    if config.transport == "sse":
        async with sse_client(config.url) as (read, write):
            async with ClientSession(read, write) as session:
                yield session
        return

    async with streamablehttp_client(
        config.url,
        timeout=timedelta(seconds=30),
        sse_read_timeout=timedelta(minutes=5),
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            yield session


def mcp_result_to_text(result: CallToolResult) -> str:
    text_parts = [content.text for content in result.content if isinstance(content, TextContent)]
    if text_parts:
        text = "\n".join(text_parts)
    elif result.structuredContent is not None:
        text = json.dumps(result.structuredContent, ensure_ascii=False)
    else:
        text = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
    if result.isError:
        raise RuntimeError(text)
    return text


class MultiServerMCPClient:
    def __init__(self, configs: list[MCPServerConfig]):
        self.configs = {config.server_name: config for config in configs}

    async def list_tools(self, server_name: str | None = None) -> dict[str, list[Tool]]:
        selected = (
            {server_name: self.configs[server_name]}
            if server_name is not None
            else self.configs
        )
        result: dict[str, list[Tool]] = {}
        for name, config in selected.items():
            async with create_mcp_session(config) as session:
                await session.initialize()
                tools = await session.list_tools()
                result[name] = tools.tools
        return result

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> str:
        config = self.configs[server_name]
        async with create_mcp_session(config) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return mcp_result_to_text(result)

    async def get_langchain_tools(self) -> list[StructuredTool]:
        tools_by_server = await self.list_tools()
        tools: list[StructuredTool] = []
        for server_name, server_tools in tools_by_server.items():
            for mcp_tool in server_tools:
                async def call_tool(_server_name=server_name, _tool_name=mcp_tool.name, **arguments: Any) -> str:
                    return await self.call_tool(_server_name, _tool_name, arguments)

                tools.append(
                    StructuredTool(
                        name=f"{server_name}__{mcp_tool.name}",
                        description=f"[{server_name}] {mcp_tool.description or ''}",
                        args_schema=mcp_tool.inputSchema,
                        coroutine=call_tool,
                    )
                )
        return tools
