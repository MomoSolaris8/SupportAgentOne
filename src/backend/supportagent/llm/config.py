"""Backward-compatible model configuration exports.

New code should use ``resolve_model`` and ``complete_chat`` from ``supportagent.llm``.
"""

from supportagent.llm.registry import (
    DEFAULT_CHAT_MODEL,
    ModelOption as ChatModelOption,
    get_default_chat_model,
    get_model_options as get_chat_model_options,
    resolve_model,
)


def resolve_chat_model(requested_model: str | None = None) -> str:
    return resolve_model(requested_model, task="chat").provider_model


__all__ = [
    "ChatModelOption",
    "DEFAULT_CHAT_MODEL",
    "get_chat_model_options",
    "get_default_chat_model",
    "resolve_chat_model",
]
