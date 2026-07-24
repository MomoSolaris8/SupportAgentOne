import os
from dataclasses import dataclass

from .schemas import LLMTask, ModelCapability, ModelProfile, ProviderName, ProviderSettings

DEFAULT_CHAT_MODEL = "qwen-plus"


class ModelConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelOption:
    id: str
    label: str
    provider: ProviderName
    capabilities: tuple[ModelCapability, ...]
    description: str
    default: bool = False


def _base_profiles() -> dict[str, ModelProfile]:
    profiles = [
        ModelProfile(
            id="qwen-plus",
            label="Qwen Plus",
            provider="qwen",
            provider_model="qwen-plus",
            capabilities=frozenset({"text", "tools"}),
            description="Balanced model for everyday insurance assistance.",
        ),
        ModelProfile(
            id="qwen-max",
            label="Qwen Max",
            provider="qwen",
            provider_model="qwen-max",
            capabilities=frozenset({"text", "tools"}),
            description="Higher-quality Qwen model for complex questions.",
        ),
        ModelProfile(
            id="qwen3-max",
            label="Qwen3 Max",
            provider="qwen",
            provider_model="qwen3-max",
            capabilities=frozenset({"text", "tools"}),
            description="Advanced Qwen model for demanding agent tasks.",
        ),
        ModelProfile(
            id="gpt-5-mini",
            label="GPT-5 mini",
            provider="openai",
            provider_model=os.environ.get("OPENAI_CHAT_MODEL", "gpt-5-mini"),
            capabilities=frozenset({"text", "tools", "vision"}),
            description="Fast OpenAI model for well-defined tasks.",
        ),
        ModelProfile(
            id="claude-sonnet-4",
            label="Claude Sonnet 4",
            provider="anthropic",
            provider_model=os.environ.get(
                "ANTHROPIC_CHAT_MODEL",
                "claude-sonnet-4-20250514",
            ),
            capabilities=frozenset({"text", "tools", "vision"}),
            description="Anthropic model for high-quality analysis and tool use.",
        ),
        ModelProfile(
            id="kimi-k2.6",
            label="Kimi K2.6",
            provider="kimi",
            provider_model=os.environ.get("KIMI_K2_6_MODEL", "kimi-k2.6"),
            capabilities=frozenset({"text", "tools"}),
            description="Moonshot model for reasoning and agentic tasks.",
        ),
        ModelProfile(
            id="kimi-k3",
            label="Kimi K3",
            provider="kimi",
            provider_model=os.environ.get("KIMI_K3_MODEL", "kimi-k3"),
            capabilities=frozenset({"text", "tools"}),
            description="Latest Moonshot model for demanding agent tasks.",
        ),
    ]
    vision_model = os.environ.get("VISION_MODEL", "").strip()
    if vision_model and vision_model not in {profile.id for profile in profiles}:
        provider = os.environ.get("VISION_PROVIDER", "qwen").strip().lower()
        if provider not in {"qwen", "openai", "anthropic", "kimi"}:
            raise ModelConfigurationError(f"Unsupported VISION_PROVIDER: {provider}")
        profiles.append(
            ModelProfile(
                id=vision_model,
                label=vision_model,
                provider=provider,  # type: ignore[arg-type]
                provider_model=vision_model,
                capabilities=frozenset({"text", "vision"}),
                user_selectable=False,
                description="Configured image-analysis model.",
            )
        )
    return {profile.id: profile for profile in profiles}


def get_provider_settings(provider: ProviderName) -> ProviderSettings:
    if provider == "qwen":
        return ProviderSettings(
            name=provider,
            api_key=(
                os.environ.get("DASHSCOPE_API_KEY")
                or os.environ.get("EMBEDDING_API_KEY")
                or ""
            ),
            base_url=(
                os.environ.get("DASHSCOPE_BASE_URL")
                or os.environ.get("EMBEDDING_BASE_URL")
            ),
        )
    if provider == "openai":
        return ProviderSettings(
            name=provider,
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            base_url=os.environ.get("OPENAI_BASE_URL") or None,
        )
    if provider == "anthropic":
        return ProviderSettings(
            name=provider,
            api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            base_url=os.environ.get("ANTHROPIC_BASE_URL") or None,
        )
    return ProviderSettings(
        name=provider,
        api_key=os.environ.get("KIMI_API_KEY", ""),
        base_url=os.environ.get("KIMI_BASE_URL") or None,
    )


def provider_is_configured(provider: ProviderName) -> bool:
    settings = get_provider_settings(provider)
    if not settings.api_key:
        return False
    return provider not in {"qwen", "kimi"} or bool(settings.base_url)


def _configured_profile_ids() -> list[str]:
    profiles = _base_profiles()
    configured = os.environ.get("CHAT_MODELS")
    if configured:
        requested = list(
            dict.fromkeys(item.strip() for item in configured.split(",") if item.strip())
        )
        unknown = [model_id for model_id in requested if model_id not in profiles]
        if unknown:
            raise ModelConfigurationError(
                f"Unknown model ids in CHAT_MODELS: {', '.join(unknown)}"
            )
        return [
            model_id
            for model_id in requested
            if provider_is_configured(profiles[model_id].provider)
        ]

    available = [
        profile.id
        for profile in profiles.values()
        if profile.user_selectable and provider_is_configured(profile.provider)
    ]
    return available


def get_default_chat_model() -> str:
    model_ids = _configured_profile_ids()
    if not model_ids:
        raise ModelConfigurationError(
            "No chat model provider is configured. Add DashScope, OpenAI, or "
            "Anthropic, or Kimi credentials."
        )
    configured = os.environ.get("CHAT_MODEL", DEFAULT_CHAT_MODEL).strip()
    return configured if configured in model_ids else model_ids[0]


def get_model_options() -> list[ModelOption]:
    profiles = _base_profiles()
    model_ids = _configured_profile_ids()
    if not model_ids:
        return []
    default = get_default_chat_model()
    return [
        ModelOption(
            id=profiles[model_id].id,
            label=profiles[model_id].label,
            provider=profiles[model_id].provider,
            capabilities=tuple(sorted(profiles[model_id].capabilities)),
            description=profiles[model_id].description,
            default=model_id == default,
        )
        for model_id in model_ids
    ]


def _task_capability(task: LLMTask) -> ModelCapability:
    if task == "tool":
        return "tools"
    if task == "vision":
        return "vision"
    return "text"


def _task_override(task: LLMTask) -> str | None:
    env_name = {
        "chat": "CHAT_MODEL",
        "claim_review": "CLAIM_REVIEW_MODEL",
        "tool": "TOOL_MODEL",
        "vision": "VISION_MODEL",
    }[task]
    return os.environ.get(env_name, "").strip() or None


def resolve_model(
    requested_model: str | None = None,
    *,
    task: LLMTask = "chat",
) -> ModelProfile:
    profiles = _base_profiles()
    selectable = _configured_profile_ids()
    capability = _task_capability(task)

    candidates: list[str] = []
    if task == "chat" and requested_model:
        candidates.append(requested_model)
    override = _task_override(task)
    if override:
        candidates.append(override)
    candidates.extend([get_default_chat_model(), *selectable])

    for model_id in dict.fromkeys(candidates):
        profile = profiles.get(model_id)
        if profile is None or capability not in profile.capabilities:
            continue
        if task == "chat" and model_id not in selectable:
            continue
        if not provider_is_configured(profile.provider):
            continue
        return profile

    raise ModelConfigurationError(
        f"No configured model supports task={task!r} and capability={capability!r}."
    )
