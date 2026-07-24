import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request


logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    incoming = request.headers.get("x-request-id", "").strip()
    # Do not copy arbitrary header contents into logs or response headers.
    if incoming and len(incoming) <= 128 and "\r" not in incoming and "\n" not in incoming:
        return incoming
    return str(uuid4())


def register_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = _request_id(request)
        request.state.request_id = request_id
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.exception(
                "http_request_failed request_id=%s method=%s path=%s duration_ms=%.1f",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
            )
            raise

        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "http_request_completed request_id=%s method=%s path=%s status_code=%s duration_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
