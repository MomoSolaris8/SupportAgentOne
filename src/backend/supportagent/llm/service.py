from functools import lru_cache
from typing import Any

from supportagent.llm.providers import AnthropicProvider, OpenAICompatibleProvider
from supportagent.llm.providers.base import ChatProvider
from supportagent.llm.registry import get_provider_settings, resolve_model
from supportagent.llm.schemas import ChatCompletion, LLMTask, ProviderName


@lru_cache(maxsize=4)
def _provider(provider: ProviderName) -> ChatProvider:
    settings = get_provider_settings(provider)
    if not settings.api_key:
        raise RuntimeError(f"Provider {provider!r} is not configured.")
    if provider == "anthropic":
        return AnthropicProvider(settings)
    return OpenAICompatibleProvider(settings)


def clear_provider_cache() -> None:
    _provider.cache_clear()


def complete_chat(
    messages: list[dict[str, Any]],
    *,
    requested_model: str | None = None,
    task: LLMTask = "chat",
    temperature: float | None = 0,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | None = None,
) -> ChatCompletion:
    profile = resolve_model(requested_model, task=task)
    return _provider(profile.provider).complete(
        profile,
        messages,
        temperature=temperature,
        tools=tools,
        tool_choice=tool_choice,
    )
