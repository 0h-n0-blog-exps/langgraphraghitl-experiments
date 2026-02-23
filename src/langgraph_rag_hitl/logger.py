# [DEBUG] ============================================================
# Agent   : backend_dev
# Task    : Python Lambda + Pydantic + pytest 実装
# Created : 2026-02-23T18:56:39
# Updated : 2026-02-23T18:56:39
# [/DEBUG] ===========================================================

"""Structured JSON logger for LangGraph RAG HITL."""

import json
import logging
import sys
import traceback
from datetime import UTC, datetime
from typing import Any


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON with required fields."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "event": record.getMessage(),
            "level": record.levelname,
            "ts": datetime.now(tz=UTC).isoformat(),
            "logger": record.name,
        }

        # Include extra fields passed via extra={}
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "taskName",
            }
        }
        log_data.update(extra_fields)

        # Include exception info if present
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            log_data["error"] = {
                "type": exc_type.__name__ if exc_type else "Unknown",
                "message": str(exc_value),
                "stack": traceback.format_exception(exc_type, exc_value, exc_tb),
            }

        return json.dumps(log_data, ensure_ascii=False, default=str)


def get_logger(name: str) -> logging.Logger:
    """Get a structured JSON logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger with JSON formatter
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger
