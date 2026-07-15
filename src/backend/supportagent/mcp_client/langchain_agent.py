import os
from typing import Any

from supportagent.llm import resolve_chat_model
from supportagent.mcp_client.client import MultiServerMCPClient
from supportagent.mcp_client.config import local_mcp_configs


async def create_dynamic_langchain_agent() -> tuple[Any, list[Any]]:
    """Create a LangChain agent from dynamically listed MCP tools.

    This is the OmniAgent-style path:

    MCP config -> MultiServerMCPClient -> list_tools -> StructuredTool
    -> create_agent(tools=...).
    """
    from langchain.agents import create_agent
    from langchain_openai import ChatOpenAI

    mcp_client = MultiServerMCPClient(local_mcp_configs())
    tools = await mcp_client.get_langchain_tools()
    model = ChatOpenAI(
        api_key=os.environ["EMBEDDING_API_KEY"],
        base_url=os.environ["EMBEDDING_BASE_URL"],
        model=resolve_chat_model(),
    )
    agent = create_agent(model=model, tools=tools)
    return agent, tools
