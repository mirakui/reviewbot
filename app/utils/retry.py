"""Retry with exponential backoff utilities."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class RetryError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, message: str, attempts: int, last_exception: BaseException) -> None:
        """Initialize the RetryError.

        Args:
            message: Error message.
            attempts: Number of attempts made.
            last_exception: The last exception that caused the retry.
        """
        super().__init__(message)
        self.attempts = attempts
        self.__cause__ = last_exception


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    """Maximum number of retry attempts (not including the initial attempt)."""

    base_delay: float = 1.0
    """Base delay in seconds between retries."""

    max_delay: float = 60.0
    """Maximum delay in seconds (caps exponential growth)."""

    exponential_base: float = 2.0
    """Base for exponential backoff calculation."""

    jitter: bool = True
    """Whether to add random jitter to delays."""

    def calculate_delay(self, attempt: int) -> float:
        """Calculate the delay for a given retry attempt.

        Args:
            attempt: The retry attempt number (0-indexed).

        Returns:
            Delay in seconds.
        """
        delay = self.base_delay * (self.exponential_base**attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add up to 25% jitter
            jitter_range = delay * 0.25
            delay = delay + random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # Ensure non-negative

        return delay


def retry_with_backoff[T](
    func: Callable[[], T],
    config: RetryConfig | None = None,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """Execute a function with retry and exponential backoff.

    Args:
        func: The function to execute.
        config: Retry configuration. Uses defaults if not provided.
        retry_on: Tuple of exception types to retry on.

    Returns:
        The return value of the function.

    Raises:
        RetryError: If all retry attempts are exhausted.
        Exception: If an exception not in retry_on is raised.
    """
    if config is None:
        config = RetryConfig()

    last_exception: BaseException | None = None
    attempts = 0

    for attempt in range(config.max_retries + 1):
        try:
            return func()
        except retry_on as e:
            last_exception = e
            attempts = attempt + 1

            if attempt < config.max_retries:
                delay = config.calculate_delay(attempt)
                time.sleep(delay)

    assert last_exception is not None
    raise RetryError(
        f"All {attempts} attempts failed",
        attempts=attempts,
        last_exception=last_exception,
    )


async def retry_with_backoff_async[T](
    func: Callable[[], Awaitable[T]],
    config: RetryConfig | None = None,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """Execute an async function with retry and exponential backoff.

    Args:
        func: The async function to execute.
        config: Retry configuration. Uses defaults if not provided.
        retry_on: Tuple of exception types to retry on.

    Returns:
        The return value of the function.

    Raises:
        RetryError: If all retry attempts are exhausted.
        Exception: If an exception not in retry_on is raised.
    """
    if config is None:
        config = RetryConfig()

    last_exception: BaseException | None = None
    attempts = 0

    for attempt in range(config.max_retries + 1):
        try:
            return await func()
        except retry_on as e:
            last_exception = e
            attempts = attempt + 1

            if attempt < config.max_retries:
                delay = config.calculate_delay(attempt)
                await asyncio.sleep(delay)

    assert last_exception is not None
    raise RetryError(
        f"All {attempts} attempts failed",
        attempts=attempts,
        last_exception=last_exception,
    )
