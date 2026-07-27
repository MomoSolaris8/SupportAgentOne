from functools import lru_cache
from time import perf_counter
from typing import Any

from supportagent.llm.errors import LLMError, map_provider_error
from supportagent.llm.providers import AnthropicProvider, OpenAICompatibleProvider
from supportagent.llm.providers.base import ChatProvider
from supportagent.llm.registry import get_provider_settings, resolve_model
from supportagent.llm.schemas import ChatCompletion, LLMTask, ProviderName
from supportagent.llm.usage import LLMCallUsage, record_llm_usage


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
    started = perf_counter()
    try:
        completion = _provider(profile.provider).complete(
            profile,
            messages,
            temperature=temperature,
            tools=tools,
            tool_choice=tool_choice,
        )
        record_llm_usage(
            LLMCallUsage(
                provider=profile.provider,
                model_id=profile.id,
                provider_model=profile.provider_model,
                latency_ms=(perf_counter() - started) * 1000,
                usage=completion.usage,
            )
        )
        return completion
    except LLMError:
        raise
    except Exception as error:
        raise map_provider_error(
            error,
            provider=profile.provider,
            model=profile.id,
        ) from error
