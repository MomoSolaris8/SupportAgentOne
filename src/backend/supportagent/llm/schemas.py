from dataclasses import dataclass, field
from typing import Any, Literal

ProviderName = Literal["qwen", "openai", "anthropic", "kimi"]
LLMTask = Literal["chat", "claim_review", "tool", "vision"]
ModelCapability = Literal["text", "tools", "vision"]


@dataclass(frozen=True)
class ModelProfile:
    id: str
    label: str
    provider: ProviderName
    provider_model: str
    capabilities: frozenset[ModelCapability]
    user_selectable: bool = True
    description: str = ""


@dataclass(frozen=True)
class ProviderSettings:
    name: ProviderName
    api_key: str
    base_url: str | None = None


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChatCompletion:
    content: str
    model_id: str
    provider: ProviderName
    tool_calls: tuple[ToolCall, ...] = ()
