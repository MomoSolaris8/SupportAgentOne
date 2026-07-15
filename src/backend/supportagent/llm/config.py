import os
from dataclasses import dataclass


DEFAULT_CHAT_MODEL = "qwen-plus"
BUILT_IN_CHAT_MODELS = ("qwen-plus", "qwen-max", "qwen3-max")


@dataclass(frozen=True)
class ChatModelOption:
    id: str
    label: str
    default: bool = False


def _configured_model_ids() -> list[str]:
    configured = os.environ.get("CHAT_MODELS")
    model_ids = [
        model_id.strip()
        for model_id in (configured.split(",") if configured else BUILT_IN_CHAT_MODELS)
        if model_id.strip()
    ]
    default_model = os.environ.get("CHAT_MODEL", DEFAULT_CHAT_MODEL).strip() or DEFAULT_CHAT_MODEL
    if default_model not in model_ids:
        model_ids.insert(0, default_model)
    return list(dict.fromkeys(model_ids))


def get_default_chat_model() -> str:
    model_ids = _configured_model_ids()
    configured_default = os.environ.get("CHAT_MODEL", DEFAULT_CHAT_MODEL).strip() or DEFAULT_CHAT_MODEL
    return configured_default if configured_default in model_ids else model_ids[0]


def resolve_chat_model(requested_model: str | None = None) -> str:
    model_ids = _configured_model_ids()
    if requested_model and requested_model in model_ids:
        return requested_model
    return get_default_chat_model()


def get_chat_model_options() -> list[ChatModelOption]:
    default_model = get_default_chat_model()
    return [
        ChatModelOption(id=model_id, label=model_id, default=model_id == default_model)
        for model_id in _configured_model_ids()
    ]
