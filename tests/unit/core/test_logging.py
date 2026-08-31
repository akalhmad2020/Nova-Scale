import json
import logging

from app.core.logging import JsonFormatter
from app.core.request_context import request_id_context


def test_json_formatter_includes_request_id_from_context() -> None:
    formatter = JsonFormatter(
        service="test-service",
        environment="test",
    )

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    token = request_id_context.set("request-123")

    try:
        payload = json.loads(formatter.format(record))
    finally:
        request_id_context.reset(token)

    assert payload["message"] == "hello"
    assert payload["request_id"] == "request-123"


def test_json_formatter_omits_request_id_without_context() -> None:
    formatter = JsonFormatter(
        service="test-service",
        environment="test",
    )

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    payload = json.loads(formatter.format(record))

    assert payload["message"] == "hello"
    assert "request_id" not in payload


def test_json_formatter_includes_http_fields() -> None:
    formatter = JsonFormatter(
        service="test-service",
        environment="test",
    )

    record = logging.LogRecord(
        name="novascale.http",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="HTTP request completed",
        args=(),
        exc_info=None,
    )

    record.http_method = "GET"
    record.http_path = "/health"
    record.http_status_code = 200
    record.duration_ms = 12.34

    token = request_id_context.set("request-123")

    try:
        payload = json.loads(formatter.format(record))
    finally:
        request_id_context.reset(token)

    assert payload["request_id"] == "request-123"
    assert payload["http_method"] == "GET"
    assert payload["http_path"] == "/health"
    assert payload["http_status_code"] == 200
    assert payload["duration_ms"] == 12.34
