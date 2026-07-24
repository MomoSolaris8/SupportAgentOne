import json
from typing import Any

from openai import OpenAI

from supportagent.llm.schemas import (
    ChatCompletion,
    ModelProfile,
    ProviderSettings,
    ToolCall,
)


class OpenAICompatibleProvider:
    def __init__(self, settings: ProviderSettings):
        kwargs: dict[str, Any] = {"api_key": settings.api_key}
        if settings.base_url:
            kwargs["base_url"] = settings.base_url
        self.client = OpenAI(**kwargs)

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
            "messages": messages,
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
        )
