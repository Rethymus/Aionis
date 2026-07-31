"""Hermetic contract tests for the shared HTTP request policy."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import format_datetime

import pytest

from src.aionis.ingest.http_policy import (
    HostSpacingPolicy,
    HttpRequestPolicy,
    HTTPStatusError,
    RetryPolicy,
    normalize_host,
)


class FakeTime:
    def __init__(self, initial: float = 0.0) -> None:
        self.value = initial
        self.sleeps: list[float] = []
        self._lock = threading.Lock()

    def monotonic(self) -> float:
        with self._lock:
            return self.value

    def sleep(self, seconds: float) -> None:
        with self._lock:
            self.sleeps.append(seconds)
            self.value += seconds


@dataclass
class FakeResponse:
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)


def test_normalize_host_canonicalizes_urls_and_bare_hosts() -> None:
    assert normalize_host("HTTPS://EXAMPLE.COM.:443/path?token=not-part-of-key") == "example.com"
    assert normalize_host("example.com:8443") == "example.com"
    assert normalize_host("https://XN--BCHER-KVA.EXAMPLE/path") == "xn--bcher-kva.example"
    with pytest.raises(ValueError, match="hostname"):
        normalize_host("https:///missing-host")


def test_first_request_is_immediate_and_same_host_waits_two_seconds() -> None:
    fake = FakeTime()
    policy = HostSpacingPolicy(clock=fake.monotonic, sleeper=fake.sleep)

    policy.wait("https://api.example.test/first")
    policy.wait("https://API.EXAMPLE.TEST./second")

    assert fake.sleeps == [2.0]
    assert fake.monotonic() == 2.0


def test_different_hosts_have_independent_first_request_slots() -> None:
    fake = FakeTime()
    policy = HostSpacingPolicy(clock=fake.monotonic, sleeper=fake.sleep)

    policy.wait("https://one.example.test/data")
    policy.wait("https://two.example.test/data")

    assert fake.sleeps == []


def test_concurrent_same_host_calls_cannot_bypass_spacing() -> None:
    fake = FakeTime()
    policy = HostSpacingPolicy(clock=fake.monotonic, sleeper=fake.sleep)
    barrier = threading.Barrier(5)

    def reserve() -> None:
        barrier.wait()
        policy.wait("https://concurrent.example.test/data")

    threads = [threading.Thread(target=reserve) for _ in range(4)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    assert fake.sleeps == [2.0, 2.0, 2.0]
    assert fake.monotonic() == 6.0


@pytest.mark.parametrize("retryable_status", [429, 500, 503, 599])
def test_retryable_statuses_use_exponential_backoff(retryable_status: int) -> None:
    fake = FakeTime()
    responses = iter(
        [FakeResponse(retryable_status), FakeResponse(retryable_status), FakeResponse(200)]
    )
    policy = HttpRequestPolicy(clock=fake.monotonic, sleeper=fake.sleep)

    response = policy.request("https://retry.example.test/data", lambda: next(responses))

    assert response.status_code == 200
    assert fake.sleeps == [2.0, 4.0]


def test_longer_retry_after_takes_precedence_and_header_is_case_insensitive() -> None:
    fake = FakeTime()
    responses = iter([FakeResponse(429, {"retry-after": "7"}), FakeResponse(200)])
    policy = HttpRequestPolicy(clock=fake.monotonic, sleeper=fake.sleep)

    policy.request("https://retry.example.test/data", lambda: next(responses))

    assert fake.sleeps == [7.0]


def test_http_date_retry_after_is_supported_with_injected_wall_time() -> None:
    fake = FakeTime()
    now = datetime(2026, 7, 31, tzinfo=timezone.utc)
    retry_at = format_datetime(datetime(2026, 7, 31, 0, 0, 9, tzinfo=timezone.utc))
    responses = iter([FakeResponse(503, {"Retry-After": retry_at}), FakeResponse(200)])
    policy = HttpRequestPolicy(
        clock=fake.monotonic,
        sleeper=fake.sleep,
        wall_time=lambda: now.timestamp(),
    )

    policy.request("https://retry.example.test/data", lambda: next(responses))

    assert fake.sleeps == [9.0]


def test_permanent_4xx_fails_fast_without_sleep() -> None:
    fake = FakeTime()
    calls = 0

    def request() -> FakeResponse:
        nonlocal calls
        calls += 1
        return FakeResponse(404, {"Authorization": "secret"})

    policy = HttpRequestPolicy(clock=fake.monotonic, sleeper=fake.sleep)
    with pytest.raises(HTTPStatusError, match="status 404") as caught:
        policy.request("https://example.test/private?token=secret", request)

    assert caught.value.status_code == 404
    assert "secret" not in str(caught.value)
    assert calls == 1
    assert fake.sleeps == []


def test_retry_count_has_a_hard_upper_bound() -> None:
    fake = FakeTime()
    calls = 0

    def request() -> FakeResponse:
        nonlocal calls
        calls += 1
        return FakeResponse(500)

    policy = HttpRequestPolicy(
        clock=fake.monotonic,
        sleeper=fake.sleep,
        retry=RetryPolicy(max_retries=3),
    )
    with pytest.raises(HTTPStatusError) as caught:
        policy.request("https://retry.example.test/data", request)

    assert caught.value.attempts == 4
    assert calls == 4
    assert fake.sleeps == [2.0, 4.0, 8.0]


def test_per_request_retry_override_preserves_shared_spacing_and_linear_backoff() -> None:
    fake = FakeTime()
    calls = 0

    def request() -> FakeResponse:
        nonlocal calls
        calls += 1
        return FakeResponse(503)

    policy = HttpRequestPolicy(clock=fake.monotonic, sleeper=fake.sleep)
    retry = RetryPolicy(max_retries=3, backoff_base=3, backoff_mode="linear")

    with pytest.raises(HTTPStatusError) as caught:
        policy.request("https://retry.example.test/data", request, retry=retry)

    assert caught.value.attempts == 4
    assert calls == 4
    assert fake.sleeps == [3.0, 6.0, 9.0]
    assert policy.retry == RetryPolicy()


def test_configured_transport_errors_are_bounded_and_unconfigured_errors_fail_fast() -> None:
    fake = FakeTime()
    calls = 0

    def failing() -> FakeResponse:
        nonlocal calls
        calls += 1
        raise OSError("connection reset")

    policy = HttpRequestPolicy(
        clock=fake.monotonic,
        sleeper=fake.sleep,
        retry=RetryPolicy(max_retries=1),
        retry_exceptions=(OSError,),
    )
    with pytest.raises(OSError, match="connection reset"):
        policy.request("https://retry.example.test/data", failing)
    assert calls == 2
    assert fake.sleeps == [2.0]

    immediate = HttpRequestPolicy(clock=fake.monotonic, sleeper=fake.sleep)
    with pytest.raises(OSError, match="connection reset"):
        immediate.request("https://other.example.test/data", failing)
    assert calls == 3
    assert fake.sleeps == [2.0]


def test_policy_rejects_weaker_spacing_or_backoff_and_invalid_retry_bounds() -> None:
    with pytest.raises(ValueError, match="at least 2.0"):
        HostSpacingPolicy(min_interval=1.99)
    with pytest.raises(ValueError, match="at least 2.0"):
        RetryPolicy(backoff_base=1.99)
    with pytest.raises(ValueError, match="negative"):
        RetryPolicy(max_retries=-1)
    with pytest.raises(ValueError, match="backoff_mode"):
        RetryPolicy(backoff_mode="quadratic")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="retry bound"):
        RetryPolicy(max_retries=1).delay(2)
