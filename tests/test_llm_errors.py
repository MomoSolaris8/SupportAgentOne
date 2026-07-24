import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import supportagent.llm.service as llm_service
from supportagent.api.exception_handlers import register_exception_handlers
from supportagent.llm.errors import (
    LLMAuthenticationError,
    LLMInvalidRequestError,
    LLMModelNotFoundError,
    LLMProviderUnavailableError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTimeoutError,
    map_provider_error,
)
from supportagent.llm.schemas import ModelProfile


class ProviderError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def mapped(error: Exception):
    return map_provider_error(error, provider="kimi", model="kimi-k2.6")


def test_provider_errors_are_mapped_to_domain_errors():
    assert isinstance(mapped(ProviderError("invalid api key", 401)), LLMAuthenticationError)
    assert isinstance(mapped(ProviderError("model not found", 404)), LLMModelNotFoundError)
    assert isinstance(
        mapped(ProviderError("insufficient balance, please recharge", 429)),
        LLMQuotaExceededError,
    )
    assert isinstance(mapped(ProviderError("too many requests", 429)), LLMRateLimitError)
    assert isinstance(mapped(ProviderError("invalid temperature", 400)), LLMInvalidRequestError)
    assert isinstance(mapped(TimeoutError("timed out")), LLMTimeoutError)
    assert isinstance(mapped(ConnectionError("offline")), LLMProviderUnavailableError)


def test_complete_chat_maps_provider_sdk_errors(monkeypatch):
    profile = ModelProfile(
        id="kimi-k2.6",
        label="Kimi K2.6",
        provider="kimi",
        provider_model="kimi-k2.6",
        capabilities=frozenset({"text"}),
    )

    class BrokenProvider:
        def complete(self, *args, **kwargs):
            raise ProviderError("insufficient balance, please recharge", 429)

    monkeypatch.setattr(llm_service, "resolve_model", lambda *args, **kwargs: profile)
    monkeypatch.setattr(llm_service, "_provider", lambda provider: BrokenProvider())

    with pytest.raises(LLMQuotaExceededError) as captured:
        llm_service.complete_chat([{"role": "user", "content": "Hello"}])

    assert captured.value.provider == "kimi"
    assert captured.value.model == "kimi-k2.6"


def test_api_handler_returns_safe_stable_error_contract():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/failure")
    def failure():
        error = LLMQuotaExceededError(provider="kimi", model="kimi-k2.6")
        raise error from RuntimeError(
            "account org-secret has insufficient balance; api_key=secret"
        )

    response = TestClient(app).get("/failure")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "llm_quota_exceeded",
            "message": "Das Kontingent des ausgewählten KI-Anbieters ist aufgebraucht.",
            "provider": "kimi",
            "model": "kimi-k2.6",
            "retryable": False,
            "request_id": None,
        }
    }
    assert "org-secret" not in response.text
    assert "api_key" not in response.text
