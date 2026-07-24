from supportagent.llm.schemas import ProviderName


class LLMError(RuntimeError):
    code = "llm_error"
    public_message = "Der ausgewählte KI-Anbieter konnte die Anfrage nicht verarbeiten."
    retryable = False

    def __init__(self, *, provider: ProviderName, model: str):
        super().__init__(self.public_message)
        self.provider = provider
        self.model = model


class LLMAuthenticationError(LLMError):
    code = "llm_authentication_failed"
    public_message = "Der ausgewählte KI-Anbieter ist nicht korrekt konfiguriert."


class LLMQuotaExceededError(LLMError):
    code = "llm_quota_exceeded"
    public_message = "Das Kontingent des ausgewählten KI-Anbieters ist aufgebraucht."


class LLMRateLimitError(LLMError):
    code = "llm_rate_limited"
    public_message = "Der ausgewählte KI-Anbieter ist vorübergehend ausgelastet."
    retryable = True


class LLMInvalidRequestError(LLMError):
    code = "llm_invalid_request"
    public_message = "Der ausgewählte KI-Anbieter hat die generierte Anfrage abgelehnt."


class LLMModelNotFoundError(LLMError):
    code = "llm_model_unavailable"
    public_message = "Das ausgewählte KI-Modell ist nicht verfügbar."


class LLMProviderUnavailableError(LLMError):
    code = "llm_provider_unavailable"
    public_message = "Der ausgewählte KI-Anbieter ist vorübergehend nicht verfügbar."
    retryable = True


class LLMTimeoutError(LLMError):
    code = "llm_timeout"
    public_message = "Die Anfrage an den ausgewählten KI-Anbieter hat zu lange gedauert."
    retryable = True


def map_provider_error(
    error: Exception,
    *,
    provider: ProviderName,
    model: str,
) -> LLMError:
    status_code = getattr(error, "status_code", None)
    error_name = type(error).__name__.lower()
    error_text = str(error).lower()

    if status_code in {401, 403} or "authentication" in error_name:
        error_type = LLMAuthenticationError
    elif status_code == 404 or "notfound" in error_name or "not_found" in error_name:
        error_type = LLMModelNotFoundError
    elif status_code == 429 or "ratelimit" in error_name or "rate_limit" in error_name:
        quota_markers = (
            "balance",
            "billing",
            "credit",
            "insufficient",
            "quota",
            "recharge",
        )
        error_type = (
            LLMQuotaExceededError
            if any(marker in error_text for marker in quota_markers)
            else LLMRateLimitError
        )
    elif status_code == 400 or "badrequest" in error_name or "bad_request" in error_name:
        error_type = LLMInvalidRequestError
    elif "timeout" in error_name:
        error_type = LLMTimeoutError
    else:
        error_type = LLMProviderUnavailableError

    return error_type(provider=provider, model=model)
