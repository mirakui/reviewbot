"""Unit tests for retry with backoff utility."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.utils.retry import (
    RetryConfig,
    RetryError,
    retry_with_backoff,
    retry_with_backoff_async,
)


class TestRetryConfig:
    """Tests for retry configuration."""

    def test_default_config(self) -> None:
        """Test default retry configuration values."""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter == True

    def test_custom_config(self) -> None:
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=False,
        )

        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 3.0
        assert config.jitter == False


class TestRetryWithBackoff:
    """Tests for synchronous retry with backoff."""

    def test_succeeds_on_first_try(self) -> None:
        """Test function that succeeds immediately."""
        func = MagicMock(return_value="success")

        result = retry_with_backoff(func)

        assert result == "success"
        assert func.call_count == 1

    def test_succeeds_on_retry(self) -> None:
        """Test function that fails then succeeds."""
        func = MagicMock(side_effect=[ValueError("fail"), "success"])
        config = RetryConfig(base_delay=0.01, jitter=False)

        result = retry_with_backoff(func, config=config, retry_on=(ValueError,))

        assert result == "success"
        assert func.call_count == 2

    def test_raises_after_max_retries(self) -> None:
        """Test that error is raised after max retries."""
        func = MagicMock(side_effect=ValueError("always fails"))
        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)

        with pytest.raises(RetryError) as exc_info:
            retry_with_backoff(func, config=config, retry_on=(ValueError,))

        assert func.call_count == 3  # Initial + 2 retries
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_does_not_retry_unexpected_exception(self) -> None:
        """Test that unexpected exceptions are not retried."""
        func = MagicMock(side_effect=TypeError("unexpected"))
        config = RetryConfig(max_retries=3, base_delay=0.01)

        with pytest.raises(TypeError):
            retry_with_backoff(func, config=config, retry_on=(ValueError,))

        assert func.call_count == 1

    def test_exponential_backoff_delay(self) -> None:
        """Test that delays increase exponentially."""
        delays: list[float] = []
        original_sleep = __import__("time").sleep

        def mock_sleep(seconds: float) -> None:
            delays.append(seconds)

        import time

        time.sleep = mock_sleep

        try:
            func = MagicMock(side_effect=ValueError("fail"))
            config = RetryConfig(max_retries=3, base_delay=1.0, exponential_base=2.0, jitter=False)

            with pytest.raises(RetryError):
                retry_with_backoff(func, config=config, retry_on=(ValueError,))

            # Delays should be: 1.0, 2.0, 4.0
            assert len(delays) == 3
            assert delays[0] == 1.0
            assert delays[1] == 2.0
            assert delays[2] == 4.0
        finally:
            time.sleep = original_sleep

    def test_max_delay_cap(self) -> None:
        """Test that delay is capped at max_delay."""
        delays: list[float] = []

        def mock_sleep(seconds: float) -> None:
            delays.append(seconds)

        import time

        original_sleep = time.sleep
        time.sleep = mock_sleep

        try:
            func = MagicMock(side_effect=ValueError("fail"))
            config = RetryConfig(
                max_retries=5,
                base_delay=10.0,
                max_delay=15.0,
                exponential_base=2.0,
                jitter=False,
            )

            with pytest.raises(RetryError):
                retry_with_backoff(func, config=config, retry_on=(ValueError,))

            # All delays should be capped at 15.0
            for delay in delays:
                assert delay <= 15.0
        finally:
            time.sleep = original_sleep


class TestRetryWithBackoffAsync:
    """Tests for asynchronous retry with backoff."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self) -> None:
        """Test async function that succeeds immediately."""
        func = AsyncMock(return_value="success")

        result = await retry_with_backoff_async(func)

        assert result == "success"
        assert func.call_count == 1

    @pytest.mark.asyncio
    async def test_succeeds_on_retry(self) -> None:
        """Test async function that fails then succeeds."""
        func = AsyncMock(side_effect=[ValueError("fail"), "success"])
        config = RetryConfig(base_delay=0.01, jitter=False)

        result = await retry_with_backoff_async(func, config=config, retry_on=(ValueError,))

        assert result == "success"
        assert func.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self) -> None:
        """Test that error is raised after max retries for async."""
        func = AsyncMock(side_effect=ValueError("always fails"))
        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)

        with pytest.raises(RetryError) as exc_info:
            await retry_with_backoff_async(func, config=config, retry_on=(ValueError,))

        assert func.call_count == 3
        assert isinstance(exc_info.value.__cause__, ValueError)

    @pytest.mark.asyncio
    async def test_does_not_retry_unexpected_exception(self) -> None:
        """Test that unexpected exceptions are not retried for async."""
        func = AsyncMock(side_effect=TypeError("unexpected"))
        config = RetryConfig(max_retries=3, base_delay=0.01)

        with pytest.raises(TypeError):
            await retry_with_backoff_async(func, config=config, retry_on=(ValueError,))

        assert func.call_count == 1
