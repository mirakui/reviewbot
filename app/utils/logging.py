"""Structured JSON logging for reviewbot."""

import json
import logging
import os
import traceback
from datetime import UTC, datetime
from typing import Any, ClassVar


class JsonFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    # Fields that are part of the standard LogRecord but not useful in JSON output
    RESERVED_ATTRS: ClassVar[set[str]] = {
        "name",
        "msg",
        "args",
        "created",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "exc_info",
        "exc_text",
        "thread",
        "threadName",
        "taskName",
        "message",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON.

        Args:
            record: The log record to format.

        Returns:
            JSON-formatted string.
        """
        # Build the base log entry
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add location info for debugging
        if record.levelno >= logging.WARNING:
            log_entry["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = "".join(traceback.format_exception(*record.exc_info))

        # Add any extra fields from the log record
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS and not key.startswith("_"):
                try:
                    # Ensure value is JSON serializable
                    json.dumps(value)
                    log_entry[key] = value
                except (TypeError, ValueError):
                    log_entry[key] = str(value)

        return json.dumps(log_entry, default=str)


def configure_logging(name: str = "reviewbot") -> logging.Logger:
    """Configure structured JSON logging for the application.

    Args:
        name: The root logger name.

    Returns:
        Configured logger instance.
    """
    # Get log level from environment, default to INFO
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    try:
        log_level = getattr(logging, log_level_str)
    except AttributeError:
        log_level = logging.INFO

    # Create or get the logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create console handler with JSON formatter
    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(module_name: str) -> logging.Logger:
    """Get a child logger for a specific module.

    Args:
        module_name: The module name to create a child logger for.

    Returns:
        Child logger instance.
    """
    return logging.getLogger(f"reviewbot.{module_name}")
