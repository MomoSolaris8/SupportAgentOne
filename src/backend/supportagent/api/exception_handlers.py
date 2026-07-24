import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from supportagent.llm.errors import (
    LLMAuthenticationError,
    LLMError,
    LLMInvalidRequestError,
    LLMModelNotFoundError,
    LLMProviderUnavailableError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTimeoutError,
)


LLM_ERROR_STATUS = {
    LLMAuthenticationError: 503,
    LLMQuotaExceededError: 503,
    LLMRateLimitError: 429,
    LLMInvalidRequestError: 502,
    LLMModelNotFoundError: 503,
    LLMProviderUnavailableError: 503,
    LLMTimeoutError: 504,
}

logger = logging.getLogger(__name__)


async def llm_exception_handler(request: Request, error: LLMError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        "llm_request_failed request_id=%s code=%s provider=%s model=%s retryable=%s",
        request_id,
        error.code,
        error.provider,
        error.model,
        error.retryable,
    )
    return JSONResponse(
        status_code=LLM_ERROR_STATUS.get(type(error), 500),
        content={
            "error": {
                "code": error.code,
                "message": error.public_message,
                "provider": error.provider,
                "model": error.model,
                "retryable": error.retryable,
                "request_id": request_id,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(LLMError, llm_exception_handler)
