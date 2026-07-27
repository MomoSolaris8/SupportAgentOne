import json
from typing import Any

from openai import OpenAI

from supportagent.llm.schemas import (
    ChatCompletion,
    ModelProfile,
    ProviderSettings,
    TokenUsage,
    ToolCall,
)


class OpenAICompatibleProvider:
    def __init__(self, settings: ProviderSettings):
        kwargs: dict[str, Any] = {"api_key": settings.api_key}
        if settings.base_url:
            kwargs["base_url"] = settings.base_url
        self.client = OpenAI(**kwargs)

    @staticmethod
    def _convert_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted = []
        for message in messages:
            tool_calls = message.get("tool_calls")
            if message.get("role") != "assistant" or not tool_calls:
                converted.append(message)
                continue

            converted_calls = []
            for call in tool_calls:
                if "function" in call:
                    converted_calls.append(call)
                    continue
                converted_calls.append(
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(
                                call.get("arguments", {}),
                                ensure_ascii=False,
                            ),
                        },
                    }
                )
            converted.append({**message, "tool_calls": converted_calls})
        return converted

    def complete(
        self,
        profile: ModelProfile,
        messages: list[dict[str, Any]],
        *,
        temperature: float | None = 0,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> ChatCompletion:
        kwargs: dict[str, Any] = {
            "model": profile.provider_model,
            "messages": self._convert_messages(messages),
        }
        omits_temperature = (
            profile.provider == "openai"
            and profile.provider_model.startswith("gpt-5")
        ) or profile.provider == "kimi"
        if temperature is not None and not omits_temperature:
            kwargs["temperature"] = temperature
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"

        response = self.client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        usage = getattr(response, "usage", None)
        prompt_details = getattr(usage, "prompt_tokens_details", None)
        completion_details = getattr(usage, "completion_tokens_details", None)
        parsed_calls = []
        for call in message.tool_calls or []:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}
            parsed_calls.append(
                ToolCall(
                    id=call.id,
                    name=call.function.name,
                    arguments=arguments,
                )
            )
        return ChatCompletion(
            content=(message.content or "").strip(),
            model_id=profile.id,
            provider=profile.provider,
            tool_calls=tuple(parsed_calls),
            usage=TokenUsage(
                input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
                output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
                cached_input_tokens=int(
                    getattr(prompt_details, "cached_tokens", 0) or 0
                ),
                reasoning_tokens=int(
                    getattr(completion_details, "reasoning_tokens", 0) or 0
                ),
            ),
        )
