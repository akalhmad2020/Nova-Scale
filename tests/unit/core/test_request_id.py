import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exception_handlers import unhandled_exception_handler
from app.core.logging import JsonFormatter
from app.core.request_id import RequestIdMiddleware


class CapturingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []
        self.setFormatter(
            JsonFormatter(
                service="test-service",
                environment="test",
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(self.format(record))


def test_unhandled_exception_is_logged_with_request_context() -> None:
    application = FastAPI()
    application.add_middleware(RequestIdMiddleware)

    @application.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    logger = logging.getLogger("novascale.http")
    handler = CapturingHandler()
    logger.addHandler(handler)

    try:
        with TestClient(
            application,
            raise_server_exceptions=False,
        ) as client:
            response = client.get(
                "/boom",
                headers={"X-Request-ID": "error-test-123"},
            )

        assert response.status_code == 500

        assert len(handler.messages) == 1

        log_message = handler.messages[0]

        assert '"message": "Unhandled exception during HTTP request"' in log_message
        assert '"request_id": "error-test-123"' in log_message
        assert '"http_method": "GET"' in log_message
        assert '"http_path": "/boom"' in log_message
        assert '"http_status_code": 500' in log_message
        assert '"duration_ms":' in log_message
        assert '"exception":' in log_message
        assert "RuntimeError: boom" in log_message

    finally:
        logger.removeHandler(handler)


def test_unhandled_exception_response_includes_request_id() -> None:
    application = FastAPI()
    application.add_exception_handler(
        Exception,
        unhandled_exception_handler,
    )
    application.add_middleware(RequestIdMiddleware)

    @application.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    with TestClient(
        application,
        raise_server_exceptions=False,
    ) as client:
        response = client.get(
            "/boom",
            headers={"X-Request-ID": "error-response-123"},
        )

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "error-response-123"
