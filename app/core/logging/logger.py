"""Application logging helpers."""

import json
import logging
import os
from datetime import datetime
from typing import Any

_LOGGER_NAME = "todo_api"
_RESERVED_RECORD_FIELDS = {
    "args",
    "msg",
    "levelname",
    "levelno",
    "created",
    "msecs",
    "relativeCreated",
    "pathname",
    "filename",
    "module",
    "lineno",
    "funcName",
    "stack_info",
    "exc_text",
    "exc_info",
    "thread",
    "threadName",
    "processName",
    "process",
}


class JsonFormatter(logging.Formatter):
    """Serialize log records into structured JSON."""

    default_time_format = "%Y-%m-%dT%H:%M:%S"
    default_msec_format = "%s.%03d"

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        log_record: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key.startswith("_"):
                continue
            if key in log_record or key in _RESERVED_RECORD_FIELDS:
                continue
            log_record[key] = value

        return json.dumps(log_record, default=self._serialize_default)

    @staticmethod
    def _serialize_default(obj: Any) -> str:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)


def get_logger(name: str | None = None) -> logging.Logger:
    logger_name = name or _LOGGER_NAME
    logger = logging.getLogger(logger_name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = JsonFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        env_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(env_level)
        logger.propagate = False
    return logger
