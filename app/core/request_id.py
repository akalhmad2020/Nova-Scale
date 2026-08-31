import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.request_context import request_id_context

logger = logging.getLogger("novascale.http")


class RequestIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())

        request.state.request_id = request_id

        token = request_id_context.set(request_id)
        started_at = perf_counter()

        try:
            response = await call_next(request)

            duration_ms = (perf_counter() - started_at) * 1000

            response.headers["X-Request-ID"] = request_id

            logger.info(
                "HTTP request completed",
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            return response

        except Exception:
            duration_ms = (perf_counter() - started_at) * 1000

            logger.exception(
                "Unhandled exception during HTTP request",
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status_code": 500,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            raise

        finally:
            request_id_context.reset(token)
