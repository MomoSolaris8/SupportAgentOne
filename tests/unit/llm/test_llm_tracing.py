import json

import pytest

import supportagent.llm.service as llm_service
from supportagent.llm.errors import LLMError
from supportagent.llm.schemas import ChatCompletion, ModelProfile, TokenUsage

PROFILE = ModelProfile(
    id="qwen-plus",
    label="Qwen Plus",
    provider="qwen",
    provider_model="qwen-plus",
    capabilities=frozenset({"text"}),
)


@pytest.fixture(autouse=True)
def use_test_profile(monkeypatch):
    monkeypatch.setattr(llm_service, "resolve_model", lambda *args, **kwargs: PROFILE)


def use_provider(monkeypatch, complete):
    provider = type("Provider", (), {"complete": staticmethod(complete)})()
    monkeypatch.setattr(llm_service, "_provider", lambda name: provider)


def test_llm_call_is_traced_as_a_generation_with_token_usage(monkeypatch, langfuse_spans):
    use_provider(
        monkeypatch,
        lambda *args, **kwargs: ChatCompletion(
            content="answer",
            model_id="qwen-plus",
            provider="qwen",
            usage=TokenUsage(input_tokens=80, output_tokens=20),
        ),
    )

    llm_service.complete_chat([{"role": "user", "content": "Hello"}])

    [span] = langfuse_spans()
    assert span.name == "llm:chat"
    assert span.attributes["langfuse.observation.type"] == "generation"
    assert span.attributes["langfuse.observation.model.name"] == "qwen-plus"
    assert json.loads(span.attributes["langfuse.observation.usage_details"]) == {"input": 80, "output": 20}


def test_failed_llm_call_is_traced_as_an_error(monkeypatch, langfuse_spans):
    def fail(*args, **kwargs):
        raise RuntimeError("model not found")

    use_provider(monkeypatch, fail)

    with pytest.raises(LLMError):
        llm_service.complete_chat([{"role": "user", "content": "Hello"}])

    [span] = langfuse_spans()
    assert span.attributes["langfuse.observation.level"] == "ERROR"
