from fastapi import FastAPI
from fastapi.testclient import TestClient

from supportagent.api.exception_handlers import register_exception_handlers
from supportagent.api.middleware import register_request_logging
from supportagent.llm.errors import LLMQuotaExceededError


def test_api_handler_returns_safe_stable_error_contract():
    app = FastAPI()
    register_request_logging(app)
    register_exception_handlers(app)

    @app.get("/failure")
    def failure():
        error = LLMQuotaExceededError(
            provider="kimi",
            model="kimi-k2.6",
        )
        raise error from RuntimeError(
            "account org-secret has insufficient balance; api_key=secret"
        )

    response = TestClient(app).get("/failure")

    assert response.status_code == 503

    error_body = response.json()["error"]

    assert error_body["code"] == "llm_quota_exceeded"
    assert error_body["message"] == (
        "Das Kontingent des ausgewählten KI-Anbieters ist aufgebraucht."
    )
    assert error_body["provider"] == "kimi"
    assert error_body["model"] == "kimi-k2.6"
    assert error_body["retryable"] is False
    assert error_body["request_id"]
    assert response.headers["X-Request-ID"] == error_body["request_id"]
    assert "org-secret" not in response.text
    assert "api_key" not in response.text
