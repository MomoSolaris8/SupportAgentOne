from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator

from supportagent.llm.schemas import ProviderName, TokenUsage


@dataclass(frozen=True)
class LLMCallUsage:
    provider: ProviderName
    model_id: str
    provider_model: str
    latency_ms: float
    usage: TokenUsage


_usage_collector: ContextVar[list[LLMCallUsage] | None] = ContextVar(
    "supportagent_llm_usage_collector",
    default=None,
)


@contextmanager
def capture_llm_usage() -> Iterator[list[LLMCallUsage]]:
    records: list[LLMCallUsage] = []
    token = _usage_collector.set(records)
    try:
        yield records
    finally:
        _usage_collector.reset(token)


def record_llm_usage(record: LLMCallUsage) -> None:
    collector = _usage_collector.get()
    if collector is not None:
        collector.append(record)
