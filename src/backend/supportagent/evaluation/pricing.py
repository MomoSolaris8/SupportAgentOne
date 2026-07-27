import json
from pathlib import Path

from pydantic import BaseModel, Field

from supportagent.llm.usage import LLMCallUsage


class ModelPrice(BaseModel):
    input_per_million: float = Field(ge=0)
    output_per_million: float = Field(ge=0)
    cached_input_per_million: float | None = Field(default=None, ge=0)
    cache_creation_input_per_million: float | None = Field(default=None, ge=0)
    source: str


class PricingCatalog(BaseModel):
    currency: str
    effective_date: str
    models: dict[str, ModelPrice]

    def estimate(self, calls: list[LLMCallUsage]) -> float | None:
        total = 0.0
        for call in calls:
            price = self.models.get(call.model_id)
            if price is None:
                return None
            cached_tokens = min(
                call.usage.cached_input_tokens,
                call.usage.input_tokens,
            )
            cache_creation_tokens = min(
                call.usage.cache_creation_input_tokens,
                max(call.usage.input_tokens - cached_tokens, 0),
            )
            regular_input_tokens = max(
                call.usage.input_tokens
                - cached_tokens
                - cache_creation_tokens,
                0,
            )
            cached_rate = (
                price.cached_input_per_million
                if price.cached_input_per_million is not None
                else price.input_per_million
            )
            cache_creation_rate = (
                price.cache_creation_input_per_million
                if price.cache_creation_input_per_million is not None
                else price.input_per_million
            )
            total += (
                regular_input_tokens * price.input_per_million
                + cached_tokens * cached_rate
                + cache_creation_tokens * cache_creation_rate
                + call.usage.output_tokens * price.output_per_million
            ) / 1_000_000
        return total


def load_pricing_catalog(path: Path | None) -> PricingCatalog | None:
    if path is None:
        return None
    return PricingCatalog.model_validate(
        json.loads(path.read_text(encoding="utf-8"))
    )
