import pytest

from supportagent.llm.registry import (
    ModelConfigurationError,
    get_model_options,
    get_provider_settings,
    resolve_model,
)


def clear_model_environment(monkeypatch):
    for name in (
        "ANTHROPIC_API_KEY",
        "CHAT_MODEL",
        "CHAT_MODELS",
        "CLAIM_REVIEW_MODEL",
        "DASHSCOPE_API_KEY",
        "DASHSCOPE_BASE_URL",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "EMBEDDING_API_KEY",
        "EMBEDDING_BASE_URL",
        "KIMI_API_KEY",
        "KIMI_BASE_URL",
        "KIMI_K2_6_MODEL",
        "KIMI_K3_MODEL",
        "OPENAI_API_KEY",
        "TOOL_MODEL",
        "VISION_MODEL",
        "VISION_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)


def test_model_options_only_expose_configured_providers(monkeypatch):
    clear_model_environment(monkeypatch)
    monkeypatch.setenv("CHAT_MODELS", "qwen-plus,gpt-5-mini,claude-sonnet-4")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "qwen-key")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://qwen.example/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

    options = get_model_options()

    assert [option.id for option in options] == ["qwen-plus", "gpt-5-mini"]
    assert [option.provider for option in options] == ["qwen", "openai"]
    assert options[0].default is True


def test_chat_honors_user_selection_within_allowlist(monkeypatch):
    clear_model_environment(monkeypatch)
    monkeypatch.setenv("CHAT_MODELS", "qwen-plus,gpt-5-mini")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "qwen-key")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://qwen.example/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

    selected = resolve_model("gpt-5-mini", task="chat")

    assert selected.provider == "openai"
    assert selected.provider_model == "gpt-5-mini"


def test_kimi_models_are_exposed_and_resolved_independently(monkeypatch):
    clear_model_environment(monkeypatch)
    monkeypatch.setenv("CHAT_MODELS", "kimi-k2.6,kimi-k3")
    monkeypatch.setenv("CHAT_MODEL", "kimi-k3")
    monkeypatch.setenv("KIMI_API_KEY", "kimi-key")
    monkeypatch.setenv("KIMI_BASE_URL", "https://api.moonshot.example/v1")

    options = get_model_options()
    selected = resolve_model("kimi-k2.6", task="chat")

    assert [option.id for option in options] == ["kimi-k2.6", "kimi-k3"]
    assert [option.provider for option in options] == ["kimi", "kimi"]
    assert options[1].default is True
    assert selected.provider == "kimi"
    assert selected.provider_model == "kimi-k2.6"


def test_claim_review_uses_backend_policy_instead_of_ui_choice(monkeypatch):
    clear_model_environment(monkeypatch)
    monkeypatch.setenv("CHAT_MODELS", "qwen-plus,gpt-5-mini,claude-sonnet-4")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "qwen-key")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://qwen.example/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setenv("CLAIM_REVIEW_MODEL", "claude-sonnet-4")

    selected = resolve_model("gpt-5-mini", task="claim_review")

    assert selected.id == "claude-sonnet-4"
    assert selected.provider == "anthropic"


def test_backend_task_ignores_ui_choice_without_an_override(monkeypatch):
    clear_model_environment(monkeypatch)
    monkeypatch.setenv("CHAT_MODELS", "qwen-plus,gpt-5-mini")
    monkeypatch.setenv("CHAT_MODEL", "qwen-plus")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "qwen-key")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://qwen.example/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

    selected = resolve_model("gpt-5-mini", task="tool")

    assert selected.id == "qwen-plus"
    assert selected.provider == "qwen"


def test_tool_policy_requires_tool_capability(monkeypatch):
    clear_model_environment(monkeypatch)
    monkeypatch.setenv("CHAT_MODELS", "qwen-plus")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "qwen-key")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://qwen.example/v1")
    monkeypatch.setenv("VISION_MODEL", "qwen-vl-plus")
    monkeypatch.setenv("TOOL_MODEL", "qwen-vl-plus")

    selected = resolve_model(task="tool")

    assert selected.id == "qwen-plus"


def test_missing_provider_configuration_is_explicit(monkeypatch):
    clear_model_environment(monkeypatch)
    monkeypatch.setenv("CHAT_MODELS", "gpt-5-mini")

    assert get_model_options() == []
    with pytest.raises(ModelConfigurationError, match="No chat model provider"):
        resolve_model("gpt-5-mini", task="chat")


def test_unknown_model_in_allowlist_is_rejected(monkeypatch):
    clear_model_environment(monkeypatch)
    monkeypatch.setenv("CHAT_MODELS", "made-up-model")

    with pytest.raises(ModelConfigurationError, match="Unknown model ids"):
        get_model_options()


def test_deepseek_uses_its_own_api_key(monkeypatch):
    clear_model_environment(monkeypatch)
    monkeypatch.setenv("CHAT_MODELS", "qwen-plus,deepseek-v4-pro")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "qwen-key")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://qwen.example/v1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")

    selected = resolve_model("deepseek-v4-pro", task="chat")
    settings = get_provider_settings("deepseek")

    assert selected.provider == "deepseek"
    assert selected.provider_model == "deepseek-v4-pro"
    assert settings.api_key == "deepseek-key"
    assert settings.base_url == "https://api.deepseek.com"


def test_deepseek_is_hidden_without_its_api_key(monkeypatch):
    clear_model_environment(monkeypatch)
    monkeypatch.setenv("CHAT_MODELS", "qwen-plus,deepseek-v4-pro")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "qwen-key")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://qwen.example/v1")

    options = get_model_options()

    assert [option.id for option in options] == ["qwen-plus"]


def test_latest_qwen_max_is_available(monkeypatch):
    clear_model_environment(monkeypatch)
    monkeypatch.setenv("CHAT_MODELS", "qwen-plus,qwen3.8-max")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "qwen-key")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://qwen.example/v1")

    selected = resolve_model("qwen3.8-max", task="chat")

    assert selected.provider_model == "qwen3.8-max"


def test_retired_qwen3_max_is_rejected(monkeypatch):
    clear_model_environment(monkeypatch)
    monkeypatch.setenv("CHAT_MODELS", "qwen-plus,qwen3-max")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "qwen-key")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://qwen.example/v1")

    with pytest.raises(ModelConfigurationError, match="qwen3-max"):
        get_model_options()
