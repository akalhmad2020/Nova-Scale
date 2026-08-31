import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.request_context import get_request_id


class JsonFormatter(logging.Formatter):
    def __init__(
        self,
        *,
        service: str,
        environment: str,
    ) -> None:
        super().__init__()
        self._service = service
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": self._service,
            "environment": self._environment,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = get_request_id()

        if request_id is not None:
            payload["request_id"] = request_id

        for field in (
            "http_method",
            "http_path",
            "http_status_code",
            "duration_ms",
            "poll_interval_seconds",
            "message_count",
            "discovered",
            "delivered",
            "retryable_failures",
            "skipped",
            "unexpected_failures",
        ):
            if hasattr(record, field):
                payload[field] = getattr(record, field)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging(
    level: str = "INFO",
    *,
    service: str,
    environment: str,
) -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())

    formatter = JsonFormatter(
        service=service,
        environment=environment,
    )

    if root.handlers:
        for handler in root.handlers:
            handler.setFormatter(formatter)
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)

    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.disabled = True
