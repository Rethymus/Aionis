"""Shared, injectable HTTP request spacing and retry policies."""

from __future__ import annotations

import ipaddress
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Literal, Protocol, TypeVar
from urllib.parse import urlsplit


class ResponseLike(Protocol):
    """The response surface needed by :class:`HttpRequestPolicy`."""

    status_code: int
    headers: Mapping[str, str]


ResponseT = TypeVar("ResponseT", bound=ResponseLike)


def normalize_host(url_or_host: str) -> str:
    """Return a stable, case-insensitive hostname key for a URL or bare host."""
    value = url_or_host.strip()
    if not value:
        raise ValueError("URL or host must not be empty")

    parsed = urlsplit(value if "://" in value or value.startswith("//") else f"//{value}")
    try:
        hostname = parsed.hostname
    except ValueError as exc:
        raise ValueError("URL or host has an invalid hostname") from exc
    if not hostname:
        raise ValueError("URL or host must contain a hostname")

    hostname = hostname.rstrip(".").lower()
    if not hostname:
        raise ValueError("URL or host must contain a hostname")
    try:
        return ipaddress.ip_address(hostname).compressed
    except ValueError:
        try:
            return hostname.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ValueError("URL or host has an invalid hostname") from exc


class HostSpacingPolicy:
    """Serialize request slots per host using a monotonic clock."""

    def __init__(
        self,
        min_interval: float = 2.0,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if min_interval < 2.0:
            raise ValueError("min_interval must be at least 2.0 seconds")
        self.min_interval = float(min_interval)
        self._clock = clock
        self._sleep = sleeper
        self._state_lock = threading.Lock()
        self._host_locks: dict[str, threading.Lock] = {}
        self._last_request: dict[str, float] = {}

    def wait(self, url_or_host: str) -> None:
        """Wait for and reserve the next request slot for ``url_or_host``."""
        host = normalize_host(url_or_host)
        with self._state_lock:
            host_lock = self._host_locks.setdefault(host, threading.Lock())

        with host_lock:
            previous = self._last_request.get(host)
            now = self._clock()
            if previous is not None:
                target = previous + self.min_interval
                while now < target:
                    self._sleep(target - now)
                    now = self._clock()
            self._last_request[host] = now


class HTTPStatusError(RuntimeError):
    """An HTTP response status rejected by the bounded retry policy."""

    def __init__(self, status_code: int, attempts: int) -> None:
        self.status_code = status_code
        self.attempts = attempts
        message = f"HTTP request failed with status {status_code} after {attempts} attempt(s)"
        super().__init__(message)


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded retry settings for retryable HTTP statuses."""

    max_retries: int = 3
    backoff_base: float = 2.0
    backoff_mode: Literal["exponential", "linear"] = "exponential"

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must not be negative")
        if self.backoff_base < 2.0:
            raise ValueError("backoff_base must be at least 2.0 seconds")
        if self.backoff_mode not in ("exponential", "linear"):
            raise ValueError("backoff_mode must be 'exponential' or 'linear'")

    @staticmethod
    def is_retryable(status_code: int) -> bool:
        return status_code == 429 or 500 <= status_code <= 599

    def delay(
        self,
        retry_number: int,
        headers: Mapping[str, str] | None = None,
        *,
        wall_time: Callable[[], float] = time.time,
    ) -> float:
        """Return the delay before a one-based retry, honoring longer Retry-After."""
        if not 1 <= retry_number <= self.max_retries:
            raise ValueError("retry_number is outside the configured retry bound")
        if self.backoff_mode == "linear":
            configured = self.backoff_base * retry_number
        else:
            configured = self.backoff_base * (2 ** (retry_number - 1))
        return max(configured, _retry_after_seconds(headers, wall_time=wall_time))


def _retry_after_seconds(
    headers: Mapping[str, str] | None, *, wall_time: Callable[[], float]
) -> float:
    if not headers:
        return 0.0
    value = next((v for k, v in headers.items() if k.lower() == "retry-after"), None)
    if value is None:
        return 0.0
    try:
        return max(0.0, float(value.strip()))
    except (TypeError, ValueError, AttributeError):
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            now = datetime.fromtimestamp(wall_time(), tz=timezone.utc)
            return max(0.0, (retry_at - now).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return 0.0


class HttpRequestPolicy:
    """Apply host spacing and bounded status/exception retries to an operation."""

    def __init__(
        self,
        *,
        spacing: HostSpacingPolicy | None = None,
        retry: RetryPolicy | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        wall_time: Callable[[], float] = time.time,
        retry_exceptions: tuple[type[BaseException], ...] = (),
    ) -> None:
        self.spacing = spacing or HostSpacingPolicy(clock=clock, sleeper=sleeper)
        self.retry = retry or RetryPolicy()
        self._sleep = sleeper
        self._wall_time = wall_time
        self._retry_exceptions = retry_exceptions

    def request(
        self,
        url: str,
        operation: Callable[[], ResponseT],
        *,
        retry: RetryPolicy | None = None,
    ) -> ResponseT:
        """Run ``operation`` with spacing; return success or raise after a bounded failure."""
        retry_policy = retry or self.retry
        attempt = 1
        while True:
            self.spacing.wait(url)
            try:
                response = operation()
            except self._retry_exceptions:
                if attempt > retry_policy.max_retries:
                    raise
                self._sleep(retry_policy.delay(attempt, wall_time=self._wall_time))
                attempt += 1
                continue

            status = int(response.status_code)
            if status < 400:
                return response
            if not retry_policy.is_retryable(status) or attempt > retry_policy.max_retries:
                raise HTTPStatusError(status, attempt)

            self._sleep(retry_policy.delay(attempt, response.headers, wall_time=self._wall_time))
            attempt += 1
