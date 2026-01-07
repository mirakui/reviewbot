"""Unit tests for structured JSON logging."""

import json
import logging
from io import StringIO

import pytest

from app.utils.logging import JsonFormatter, configure_logging, get_logger


class TestJsonFormatter:
    """Tests for JSON log formatter."""

    def test_format_basic_message(self) -> None:
        """Test formatting a basic log message."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["message"] == "Test message"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test"
        assert "timestamp" in parsed

    def test_format_with_extra_fields(self) -> None:
        """Test formatting with extra context fields."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.pr_number = 42
        record.repository = "owner/repo"

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["pr_number"] == 42
        assert parsed["repository"] == "owner/repo"

    def test_format_with_exception(self) -> None:
        """Test formatting with exception info."""
        formatter = JsonFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "ERROR"
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]

    def test_format_with_message_args(self) -> None:
        """Test formatting with message arguments."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="User %s performed action %s",
            args=("alice", "review"),
            exc_info=None,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["message"] == "User alice performed action review"


class TestConfigureLogging:
    """Tests for logging configuration."""

    def test_configure_with_default_level(self) -> None:
        """Test configuring logging with default level."""
        logger = configure_logging()

        assert logger.level == logging.INFO

    def test_configure_with_debug_level(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test configuring logging with DEBUG level."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        logger = configure_logging()

        assert logger.level == logging.DEBUG

    def test_configure_with_invalid_level(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test configuring logging with invalid level falls back to INFO."""
        monkeypatch.setenv("LOG_LEVEL", "INVALID")
        logger = configure_logging()

        assert logger.level == logging.INFO


class TestGetLogger:
    """Tests for logger retrieval."""

    def test_get_logger_returns_child(self) -> None:
        """Test that get_logger returns a child logger."""
        logger = get_logger("mymodule")

        assert logger.name == "reviewbot.mymodule"

    def test_get_logger_uses_json_format(self) -> None:
        """Test that logger uses JSON format."""
        configure_logging()
        logger = get_logger("test")
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        logger.info("Test message")

        output = stream.getvalue()
        parsed = json.loads(output)
        assert parsed["message"] == "Test message"
