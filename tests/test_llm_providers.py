import base64

from supportagent.llm.providers.anthropic_provider import AnthropicProvider
from supportagent.llm.providers.openai_compatible import OpenAICompatibleProvider
from supportagent.llm.schemas import ModelProfile


def profile(provider="qwen"):
    return ModelProfile(
        id="test-model",
        label="Test model",
        provider=provider,
        provider_model="provider-model",
        capabilities=frozenset({"text", "tools"}),
    )


def test_openai_compatible_provider_normalizes_tool_calls():
    captured = {}

    class Completions:
        def create(self, **kwargs):
            captured.update(kwargs)
            function = type(
                "Function",
                (),
                {"name": "weather__get_weather", "arguments": '{"location":"Bern"}'},
            )()
            call = type("Call", (), {"id": "call-1", "function": function})()
            message = type("Message", (), {"content": "", "tool_calls": [call]})()
            choice = type("Choice", (), {"message": message})()
            return type("Response", (), {"choices": [choice]})()

    provider = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)
    provider.client = type(
        "Client",
        (),
        {"chat": type("Chat", (), {"completions": Completions()})()},
    )()
    tools = [
        {
            "type": "function",
            "function": {
                "name": "weather__get_weather",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]

    result = provider.complete(
        profile(),
        [{"role": "user", "content": "Weather in Bern"}],
        tools=tools,
    )

    assert captured["model"] == "provider-model"
    assert captured["tool_choice"] == "auto"
    assert result.tool_calls[0].name == "weather__get_weather"
    assert result.tool_calls[0].arguments == {"location": "Bern"}


def test_kimi_provider_omits_fixed_sampling_parameters():
    captured = {}

    class Completions:
        def create(self, **kwargs):
            captured.update(kwargs)
            message = type("Message", (), {"content": "ok", "tool_calls": []})()
            choice = type("Choice", (), {"message": message})()
            return type("Response", (), {"choices": [choice]})()

    provider = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)
    provider.client = type(
        "Client",
        (),
        {"chat": type("Chat", (), {"completions": Completions()})()},
    )()
    kimi_profile = ModelProfile(
        id="kimi-k2.6",
        label="Kimi K2.6",
        provider="kimi",
        provider_model="kimi-k2.6",
        capabilities=frozenset({"text", "tools"}),
    )

    provider.complete(
        kimi_profile,
        [{"role": "user", "content": "Hello"}],
        temperature=0,
    )

    assert "temperature" not in captured


def test_anthropic_provider_converts_system_images_and_tool_results():
    encoded = base64.b64encode(b"image").decode()
    system, messages = AnthropicProvider._convert_messages(
        [
            {"role": "system", "content": "Use approved evidence."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Inspect this"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{encoded}"},
                    },
                ],
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "name": "calendar__create_event",
                        "arguments": {"title": "Interview"},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call-1",
                "content": "created",
            },
        ]
    )

    assert system == "Use approved evidence."
    assert messages[0]["content"][1]["source"]["media_type"] == "image/png"
    assert messages[1]["content"][0]["type"] == "tool_use"
    assert messages[2]["content"][0]["type"] == "tool_result"


def test_anthropic_provider_converts_openai_tool_schema():
    converted = AnthropicProvider._convert_tools(
        [
            {
                "type": "function",
                "function": {
                    "name": "jira__create_issue",
                    "description": "Create an issue",
                    "parameters": {
                        "type": "object",
                        "properties": {"summary": {"type": "string"}},
                        "required": ["summary"],
                    },
                },
            }
        ]
    )

    assert converted == [
        {
            "name": "jira__create_issue",
            "description": "Create an issue",
            "input_schema": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
        }
    ]
