"""Hermetic integration tests for approved direct-request adapters."""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import requests

from aionis.features import macro_surprise
from aionis.ingest import (
    cik_resolver,
    event_text,
    events,
    fundamentals,
    market,
    stakes_13d,
    stakes_13d_efts,
    universe,
)
from aionis.ingest.http_policy import HttpRequestPolicy, HTTPStatusError


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class _Response:
    def __init__(
        self,
        *,
        status_code: int = 200,
        payload: Any = None,
        text: str = "",
        content: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.content = content
        self.headers = headers or {}

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


class _RecordingPolicy:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def request(self, url: str, operation: Any, **_: object) -> _Response:
        self.urls.append(url)
        return operation()


class _ForbiddenPolicy:
    def request(self, url: str, operation: Any) -> _Response:
        pytest.fail(f"cache hit acquired HTTP policy for {url}")


def _tarball_bytes() -> bytes:
    payload = b"AAPL\tApple Inc.\t1.0\n"
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        info = tarfile.TarInfo("repo/data/spy202401")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    return stream.getvalue()


def test_exact_approved_direct_request_allowlist_uses_shared_policy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    policy = _RecordingPolicy()
    monkeypatch.setattr(universe, "_HTTP_POLICY", policy)

    def fake_get(url: str, **kwargs: object) -> _Response:
        if "tiingo.com" in url:
            return _Response(payload=[{"date": "2024-01-02T00:00:00Z", "adjClose": 1.0}])
        if "alpaca.markets" in url:
            return _Response(payload={"bars": [{"t": "2024-01-02T00:00:00Z", "c": 1.0}]})
        if url == fundamentals._TICKERS_URL or url == cik_resolver._TICKERS_URL:
            return _Response(payload={"0": {"ticker": "AAA", "cik_str": 1}})
        if "companyfacts" in url:
            return _Response(payload={"facts": {}})
        if "submissions" in url:
            return _Response(payload={"name": "Issuer", "formerNames": [], "filings": {}})
        if "efts.sec.gov" in url:
            return _Response(payload={"hits": {"total": {"value": 0}, "hits": []}})
        if url == events._FRED_RELEASE_DATES:
            return _Response(payload={"release_dates": [{"date": "2024-01-10"}]})
        if url == macro_surprise._ALFRED_OBS_URL:
            return _Response(payload={"observations": []})
        if url == events._FOMC_CALENDAR:
            return _Response(text="<html><body>1/31/2024</body></html>")
        if "monetary20240131a.htm" in url:
            return _Response(text="<html><body>For immediate release statement</body></html>")
        if url == universe._HANSHOF_URL:
            return _Response(text='date,tickers\n2024-01-02,"AAPL"\n')
        if url == universe._PB_TARBALL:
            return _Response(content=_tarball_bytes())
        raise AssertionError(f"unexpected URL: {url}; kwargs={kwargs}")

    monkeypatch.setattr(requests, "get", fake_get)

    market._from_tiingo(["AAA"], "2024-01-01", "2024-01-31", "key")
    market._from_alpaca(["AAA"], "2024-01-01", "2024-01-31", "id", "secret")
    fundamentals.cik_map(tmp_path / "fund-map")
    fundamentals.company_facts(1, tmp_path / "fund-facts")
    stakes_13d._get_json(stakes_13d._SUBMISSIONS_URL.format(cik=1), tmp_path / "stake.json")
    stakes_13d_efts._get_json(stakes_13d_efts._EFTS_URL)
    cik_resolver._fetch_with_backoff(cik_resolver._TICKERS_URL)
    cik_resolver.cik_name_history(1, tmp_path / "cik-names")
    events.fetch_fred_release_events("key", 10, "CPI", "2024-01-01", "2024-01-31")
    macro_surprise._download_vintages("CPIAUCSL", "key")
    events.fetch_fomc_events("2024-01-01", "2024-01-31")
    assert event_text._fetch_text("FOMC", pd.Timestamp("2024-01-31"))
    universe.load_hanshof_membership(tmp_path / "hanshof")
    universe.load_pierrebrunelle_membership(tmp_path / "pierre")

    assert len(policy.urls) == 14
    assert set(policy.urls) == {
        "https://api.tiingo.com/tiingo/daily/AAA/prices",
        "https://data.alpaca.markets/v2/stocks/AAA/bars",
        fundamentals._TICKERS_URL,
        fundamentals._FACTS_URL.format(cik=1),
        stakes_13d._SUBMISSIONS_URL.format(cik=1),
        stakes_13d_efts._EFTS_URL,
        cik_resolver._SUBMISSIONS_URL.format(cik=1),
        events._FRED_RELEASE_DATES,
        macro_surprise._ALFRED_OBS_URL,
        events._FOMC_CALENDAR,
        event_text._FOMC_STATEMENT.format(yyyymmdd="20240131"),
        universe._HANSHOF_URL,
        universe._PB_TARBALL,
    }
    assert policy.urls.count(fundamentals._TICKERS_URL) == 2


def test_cache_hits_return_before_policy_acquisition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(universe, "_HTTP_POLICY", _ForbiddenPolicy())

    fund = tmp_path / "fund"
    fund.mkdir()
    (fund / "sec_tickers.json").write_text('{"AAA": 1}')
    (fund / "sec_facts_0000000001.json").write_text('{"facts": {}}')
    assert fundamentals.cik_map(fund) == {"AAA": 1}
    assert fundamentals.company_facts(1, fund) == {"facts": {}}

    stake = tmp_path / "stake.json"
    stake.write_text('{"filings": {}}')
    assert stakes_13d._get_json("https://data.sec.gov/example", stake) == {"filings": {}}
    assert stakes_13d_efts._get_json("https://efts.sec.gov/example", stake) == {
        "filings": {}
    }

    cik = tmp_path / "cik"
    cik.mkdir()
    (cik / cik_resolver._CACHE_NAME).write_text('{"AAA": 1}')
    (cik / "cik_names_0000000001.json").write_text('{"current": "A", "former": []}')
    assert cik_resolver._load_sec_ticker_map(cik) == {"AAA": 1}
    assert cik_resolver.cik_name_history(1, cik)["current"] == "A"

    macro = tmp_path / "macro"
    macro.mkdir()
    (macro / "alfred_CPIAUCSL.json").write_text(
        json.dumps(
            {
                "observations": [
                    {"date": "2024-01-01", "realtime_start": "2024-02-01", "value": "1"}
                ]
            }
        )
    )
    assert len(macro_surprise.fetch_alfred_vintages("CPIAUCSL", "key", macro)) == 1

    hanshof = tmp_path / "hanshof"
    hanshof.mkdir()
    pd.DataFrame({"date": [pd.Timestamp("2024-01-02")], "ticker": ["AAPL"]}).to_parquet(
        hanshof / "universe_hanshof.parquet"
    )
    assert len(universe.load_hanshof_membership(hanshof)) == 1

    texts = tmp_path / "texts"
    texts.mkdir()
    (texts / "FOMC_20240131.txt").write_text("cached")
    frame = pd.DataFrame(
        [{"event_id": "FOMC_20240131", "event_type": "FOMC", "event_ts": "2024-01-31"}]
    )
    assert event_text.fetch_event_text(frame, texts).iloc[0]["text"] == "cached"


def test_same_host_spacing_is_shared_across_fred_and_alfred_adapters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = _FakeClock()
    policy = HttpRequestPolicy(clock=clock.monotonic, sleeper=clock.sleep)
    monkeypatch.setattr(universe, "_HTTP_POLICY", policy)

    def fake_get(url: str, **_: object) -> _Response:
        if url == events._FRED_RELEASE_DATES:
            return _Response(payload={"release_dates": [{"date": "2024-01-10"}]})
        return _Response(payload={"observations": []})

    monkeypatch.setattr(requests, "get", fake_get)
    events.fetch_fred_release_events("key", 10, "CPI", "2024-01-01", "2024-01-31")
    macro_surprise._download_vintages("CPIAUCSL", "key")

    assert clock.sleeps == [2.0]


def test_adapter_retry_is_bounded_with_fake_clock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    clock = _FakeClock()
    policy = HttpRequestPolicy(clock=clock.monotonic, sleeper=clock.sleep)
    monkeypatch.setattr(universe, "_HTTP_POLICY", policy)
    calls = 0

    def unavailable(url: str, **_: object) -> _Response:
        nonlocal calls
        calls += 1
        return _Response(status_code=503)

    monkeypatch.setattr(requests, "get", unavailable)

    with pytest.raises(HTTPStatusError, match="after 4 attempt"):
        fundamentals.cik_map(tmp_path)

    assert calls == 4
    assert clock.sleeps == [2.0, 4.0, 8.0]


def _call_configurable_adapter(
    name: str, tmp_path: Path, *, retries: int, backoff: int
) -> object:
    if name == "tiingo":
        return market._from_tiingo(
            ["AAA"], "2024-01-01", "2024-01-31", "key", retries, backoff
        )
    if name == "alpaca":
        return market._from_alpaca(
            ["AAA"], "2024-01-01", "2024-01-31", "id", "secret", retries, backoff
        )
    if name == "fundamentals":
        return fundamentals.company_facts(1, tmp_path / "facts", retries, backoff)
    if name == "stakes_13d":
        return stakes_13d._get_json(
            stakes_13d._SUBMISSIONS_URL.format(cik=1),
            tmp_path / "stake.json",
            retries=retries,
            backoff=backoff,
        )
    if name == "stakes_13d_efts":
        return stakes_13d_efts._get_json(
            stakes_13d_efts._EFTS_URL, retries=retries, backoff=backoff
        )
    if name == "cik_resolver":
        return cik_resolver._fetch_with_backoff(
            cik_resolver._TICKERS_URL, retries=retries, backoff=backoff
        )
    raise AssertionError(f"unknown adapter: {name}")


_CONFIGURABLE_ADAPTERS = (
    "tiingo",
    "alpaca",
    "fundamentals",
    "stakes_13d",
    "stakes_13d_efts",
    "cik_resolver",
)


@pytest.mark.parametrize("adapter", _CONFIGURABLE_ADAPTERS)
def test_adapter_honors_one_total_attempt(
    adapter: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    clock = _FakeClock()
    policy = HttpRequestPolicy(clock=clock.monotonic, sleeper=clock.sleep)
    monkeypatch.setattr(universe, "_HTTP_POLICY", policy)
    calls = 0

    def unavailable(url: str, **_: object) -> _Response:
        nonlocal calls
        calls += 1
        return _Response(status_code=503)

    monkeypatch.setattr(requests, "get", unavailable)

    try:
        _call_configurable_adapter(adapter, tmp_path, retries=1, backoff=7)
    except RuntimeError:
        pass

    assert calls == 1
    assert clock.sleeps == []


@pytest.mark.parametrize("adapter", _CONFIGURABLE_ADAPTERS)
def test_adapter_honors_custom_backoff_schedule(
    adapter: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    clock = _FakeClock()
    policy = HttpRequestPolicy(clock=clock.monotonic, sleeper=clock.sleep)
    monkeypatch.setattr(universe, "_HTTP_POLICY", policy)
    calls = 0

    payloads: dict[str, object] = {
        "tiingo": [{"date": "2024-01-02T00:00:00Z", "adjClose": 1.0}],
        "alpaca": {"bars": [{"t": "2024-01-02T00:00:00Z", "c": 1.0}]},
        "fundamentals": {"facts": {}},
        "stakes_13d": {"filings": {}},
        "stakes_13d_efts": {"hits": {"total": {"value": 0}, "hits": []}},
        "cik_resolver": {"0": {"ticker": "AAA", "cik_str": 1}},
    }

    def eventually_available(url: str, **_: object) -> _Response:
        nonlocal calls
        calls += 1
        status = 503 if calls < 4 else 200
        return _Response(status_code=status, payload=payloads[adapter])

    monkeypatch.setattr(requests, "get", eventually_available)

    _call_configurable_adapter(adapter, tmp_path, retries=4, backoff=3)

    assert calls == 4
    expected = [3.0, 6.0, 12.0] if adapter == "cik_resolver" else [3.0, 6.0, 9.0]
    assert clock.sleeps == expected
