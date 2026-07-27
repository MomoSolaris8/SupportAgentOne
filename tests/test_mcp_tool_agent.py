import asyncio
from types import SimpleNamespace

import pytest

from supportagent.llm.schemas import ChatCompletion, ToolCall
from supportagent.mcp_client import tool_agent


class FakeMCPClient:
    def __init__(self, configs):
        self.configs = configs

    async def list_tools(self):
        return {
            "time_mcp": [
                SimpleNamespace(
                    name="get_current_time",
                    description="Get the current date and time for an IANA timezone.",
                    inputSchema={
                        "type": "object",
                        "properties": {"timezone": {"type": "string"}},
                    },
                )
            ]
        }

    async def call_tool(self, server_name, tool_name, arguments):
        assert server_name == "time_mcp"
        assert tool_name == "get_current_time"
        assert arguments == {"timezone": "Europe/Zurich"}
        return '{"timezone":"Europe/Zurich","time":"14:30:00","utc_offset":"+0200"}'


@pytest.mark.parametrize(
    ("question", "language", "answer"),
    [
        ("Wie spät ist es in Zürich?", "German", "In Zürich ist es 14:30 Uhr."),
        ("What time is it in Zurich?", "English", "It is 2:30 PM in Zurich."),
        ("苏黎世现在几点了？", "Chinese", "苏黎世现在是下午2:30。"),
    ],
)
def test_time_tool_answer_preserves_request_language(
    monkeypatch,
    question,
    language,
    answer,
):
    calls = []

    def fake_complete_chat(messages, **kwargs):
        calls.append(messages)
        if len(calls) == 1:
            return ChatCompletion(
                content="",
                model_id="qwen-plus",
                provider="qwen",
                tool_calls=(
                    ToolCall(
                        id="call-1",
                        name="time_mcp__get_current_time",
                        arguments={"timezone": "Europe/Zurich"},
                    ),
                ),
            )
        return ChatCompletion(
            content=answer,
            model_id="qwen-plus",
            provider="qwen",
        )

    monkeypatch.setattr(tool_agent, "dynamic_mcp_enabled", lambda: True)
    monkeypatch.setattr(tool_agent, "local_mcp_configs", lambda servers: [object()])
    monkeypatch.setattr(tool_agent, "MultiServerMCPClient", FakeMCPClient)
    monkeypatch.setattr(tool_agent, "tool_auto_allowed", lambda server, tool: True)
    monkeypatch.setattr(tool_agent, "complete_chat", fake_complete_chat)

    result = asyncio.run(
        tool_agent.run_dynamic_mcp_agent(
            question,
            enabled_mcp_servers=["time_mcp"],
            model="qwen-plus",
        )
    )

    assert result.answer == answer
    assert result.tool_calls[0].server == "time_mcp"
    assert result.tool_calls[0].tool == "get_current_time"
    assert f"respond in {language}" in calls[0][0]["content"]
    assert "Never infer a timezone from the request language" in calls[0][0]["content"]
    assert "use Europe/Zurich" in calls[0][0]["content"]
    assert calls[1][-1]["content"].endswith(f"Answer in {language}.")
