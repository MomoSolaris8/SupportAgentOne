import base64
from typing import Any

from supportagent.llm.schemas import (
    ChatCompletion,
    ModelProfile,
    ProviderSettings,
    ToolCall,
)


class AnthropicProvider:
    def __init__(self, settings: ProviderSettings):
        try:
            from anthropic import Anthropic
        except ImportError as error:
            raise RuntimeError(
                "Anthropic provider requires the 'anthropic' package."
            ) from error
        kwargs: dict[str, Any] = {"api_key": settings.api_key}
        if settings.base_url:
            kwargs["base_url"] = settings.base_url
        self.client = Anthropic(**kwargs)

    @staticmethod
    def _content_blocks(content: Any) -> Any:
        if not isinstance(content, list):
            return content
        blocks = []
        for item in content:
            if item.get("type") == "text":
                blocks.append({"type": "text", "text": item.get("text", "")})
                continue
            if item.get("type") != "image_url":
                continue
            url = item.get("image_url", {}).get("url", "")
            if not url.startswith("data:") or ";base64," not in url:
                continue
            header, encoded = url.split(",", 1)
            media_type = header[5:].split(";", 1)[0]
            base64.b64decode(encoded, validate=True)
            blocks.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": encoded,
                    },
                }
            )
        return blocks

    @classmethod
    def _convert_messages(
        cls,
        messages: list[dict[str, Any]],
    ) -> tuple[str, list[dict[str, Any]]]:
        systems = [
            str(message.get("content", ""))
            for message in messages
            if message.get("role") == "system"
        ]
        converted: list[dict[str, Any]] = []
        for message in messages:
            role = message.get("role")
            if role == "system":
                continue
            if role == "tool":
                converted.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": message["tool_call_id"],
                                "content": str(message.get("content", "")),
                            }
                        ],
                    }
                )
                continue
            content: Any = cls._content_blocks(message.get("content", ""))
            if role == "assistant" and message.get("tool_calls"):
                blocks = []
                if content:
                    blocks.append({"type": "text", "text": str(content)})
                blocks.extend(
                    {
                        "type": "tool_use",
                        "id": call["id"],
                        "name": call["name"],
                        "input": call.get("arguments", {}),
                    }
                    for call in message["tool_calls"]
                )
                content = blocks
            converted.append(
                {
                    "role": "assistant" if role == "assistant" else "user",
                    "content": content,
                }
            )
        return "\n\n".join(systems), converted

    @staticmethod
    def _convert_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        return [
            {
                "name": tool["function"]["name"],
                "description": tool["function"].get("description", ""),
                "input_schema": tool["function"].get(
                    "parameters",
                    {"type": "object", "properties": {}},
                ),
            }
            for tool in tools
        ]

    def complete(
        self,
        profile: ModelProfile,
        messages: list[dict[str, Any]],
        *,
        temperature: float | None = 0,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> ChatCompletion:
        system, converted = self._convert_messages(messages)
        kwargs: dict[str, Any] = {
            "model": profile.provider_model,
            "max_tokens": 4096,
            "messages": converted,
        }
        if system:
            kwargs["system"] = system
        if temperature is not None:
            kwargs["temperature"] = temperature
        anthropic_tools = self._convert_tools(tools)
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools
            if tool_choice == "auto" or tool_choice is None:
                kwargs["tool_choice"] = {"type": "auto"}

        response = self.client.messages.create(**kwargs)
        text = []
        calls = []
        for block in response.content:
            if block.type == "text":
                text.append(block.text)
            elif block.type == "tool_use":
                calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=dict(block.input),
                    )
                )
        return ChatCompletion(
            content="\n".join(text).strip(),
            model_id=profile.id,
            provider=profile.provider,
            tool_calls=tuple(calls),
        )
