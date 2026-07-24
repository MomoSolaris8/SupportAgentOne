from typing import Any

from supportagent.llm import resolve_model
from supportagent.llm.registry import get_provider_settings
from supportagent.mcp_client.client import MultiServerMCPClient
from supportagent.mcp_client.config import local_mcp_configs


async def create_dynamic_langchain_agent() -> tuple[Any, list[Any]]:
    """Create a LangChain agent from dynamically listed MCP tools.

    This is the OmniAgent-style path:

    MCP config -> MultiServerMCPClient -> list_tools -> StructuredTool
    -> create_agent(tools=...).
    """
    from langchain.agents import create_agent
    mcp_client = MultiServerMCPClient(local_mcp_configs())
    tools = await mcp_client.get_langchain_tools()
    profile = resolve_model(task="tool")
    settings = get_provider_settings(profile.provider)
    if profile.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        kwargs = {
            "model": profile.provider_model,
            "anthropic_api_key": settings.api_key,
        }
        if settings.base_url:
            kwargs["anthropic_api_url"] = settings.base_url
        model = ChatAnthropic(**kwargs)
    else:
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            model=profile.provider_model,
        )
    agent = create_agent(model=model, tools=tools)
    return agent, tools
