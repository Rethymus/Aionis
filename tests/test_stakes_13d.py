"""13D ingest + SIC accessor — hermetic (no network).

Pins :mod:`aionis.ingest.stakes_13d`: the SC 13D / 13D/A event stream is filtered
out of the full submissions history (10-K / SC 13G / 8-K dropped), paginated
across the ``files[]`` archive blocks, date-ranged, filed-date PIT-anchored; SIC
rides the same fetch; cache hits make no call; and the SEC-burst backoff retries
on transient errors. Mirrors the offline-vintage pattern of ``test_fundamentals``.
"""
from __future__ import annotations

import json

import pytest
import requests

from aionis.ingest import stakes_13d, universe
from aionis.ingest.http_policy import HttpRequestPolicy

CIK = 1098  # ANSYS


class _Resp:
    def __init__(self, payload, status_code=200):
        self._p = payload
        self.status_code = status_code
        self.headers = {}

    def json(self): return self._p


def _submissions(recent_rows, files=None, sic="7372"):
    return {
        "cik": str(CIK), "sic": sic, "sicDescription": f"SIC {sic} desc",
        "filings": {
            "recent": {
                "form": [r[0] for r in recent_rows],
                "filingDate": [r[1] for r in recent_rows],
                "accessionNumber": [r[2] for r in recent_rows],
                "primaryDocument": ["d.htm"] * len(recent_rows),
            },
            "files": files or [],
        },
    }


def _block(rows):
    return {
        "form": [r[0] for r in rows], "filingDate": [r[1] for r in rows],
        "accessionNumber": [r[2] for r in rows],
        "primaryDocument": ["d.htm"] * len(rows),
    }


def _install_policy(monkeypatch, sleeps=None):
    now = [0.0]

    def sleep(seconds):
        if sleeps is not None:
            sleeps.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(
        universe,
        "_HTTP_POLICY",
        HttpRequestPolicy(
            clock=lambda: now[0],
            sleeper=sleep,
            retry_exceptions=(requests.RequestException,),
        ),
    )


def _no_network(monkeypatch, url_map, sleeps=None):
    """Serve a URL map through the shared policy with fake time."""
    calls: list[str] = []

    def fake(url, headers=None, timeout=None):
        calls.append(url)
        if url in url_map:
            return _Resp(url_map[url])
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(requests, "get", fake)
    _install_policy(monkeypatch, sleeps)
    return calls


# --- form filtering ---------------------------------------------------------


def test_filings_13d_keeps_only_sc_13d_and_amendments(monkeypatch, tmp_path):
    recent = [
        ("SC 13D", "2021-03-15", "0000001098-21-000001"),
        ("SC 13D/A", "2021-04-20", "0000001098-21-000007"),
        ("SC 13G", "2021-05-01", "0000001098-21-000010"),  # passive -> drop
        ("10-K", "2021-02-28", "0000001098-21-000020"),     # not a stake -> drop
        ("8-K", "2021-06-01", "0000001098-21-000030"),      # not a stake -> drop
    ]
    url = stakes_13d._SUBMISSIONS_URL.format(cik=CIK)
    _no_network(monkeypatch, {url: _submissions(recent)})

    df = stakes_13d.filings_13d(CIK, cache_dir=tmp_path)

    assert set(df["form"]) == {"SC 13D", "SC 13D/A"}
    assert len(df) == 2
    assert df["filing_date"].is_monotonic_increasing


# --- pagination across archive blocks ---------------------------------------


def test_filings_13d_paginates_archive_blocks(monkeypatch, tmp_path):
    recent = [("SC 13D", "2024-01-10", "A-recent")]
    block_name = "CIK0000001098-18.json"
    files = [{"name": block_name, "from": "2018-01-01", "to": "2020-12-31"}]
    sub = _submissions(recent, files=files)
    block_rows = [("SC 13D", "2019-07-01", "A-archive")]
    url_map = {
        stakes_13d._SUBMISSIONS_URL.format(cik=CIK): sub,
        stakes_13d._BLOCK_URL.format(name=block_name): _block(block_rows),
    }
    calls = _no_network(monkeypatch, url_map)

    df = stakes_13d.filings_13d(CIK, cache_dir=tmp_path)

    assert set(df["accession"]) == {"A-recent", "A-archive"}
    assert stakes_13d._BLOCK_URL.format(name=block_name) in calls  # block fetched


def test_filings_13d_skips_archive_block_outside_date_range(monkeypatch, tmp_path):
    block_name = "CIK0000001098-12.json"
    files = [{"name": block_name, "from": "2012-01-01", "to": "2014-12-31"}]  # before start
    sub = _submissions([("SC 13D", "2020-06-01", "A")], files=files)
    url = stakes_13d._SUBMISSIONS_URL.format(cik=CIK)
    calls = _no_network(monkeypatch, {url: sub})

    df = stakes_13d.filings_13d(CIK, start="2016-01-01", end="2026-06-30", cache_dir=tmp_path)

    assert stakes_13d._BLOCK_URL.format(name=block_name) not in calls  # skipped
    assert len(df) == 1 and df.iloc[0]["accession"] == "A"


# --- date range on the filings themselves -----------------------------------


def test_filings_13d_respects_date_range(monkeypatch, tmp_path):
    recent = [
        ("SC 13D", "2015-06-01", "pre"),   # before start -> drop
        ("SC 13D", "2018-03-01", "in"),    # in window -> keep
        ("SC 13D", "2027-01-01", "post"),  # after end -> drop
    ]
    url = stakes_13d._SUBMISSIONS_URL.format(cik=CIK)
    _no_network(monkeypatch, {url: _submissions(recent)})

    df = stakes_13d.filings_13d(CIK, start="2016-01-01", end="2026-06-30", cache_dir=tmp_path)

    assert list(df["accession"]) == ["in"]


# --- SIC rides the same fetch ----------------------------------------------


def test_sic_for_cik_returns_code_and_description(monkeypatch, tmp_path):
    url = stakes_13d._SUBMISSIONS_URL.format(cik=CIK)
    _no_network(monkeypatch, {url: _submissions([], sic="7372")})

    code, desc = stakes_13d.sic_for_cik(CIK, cache_dir=tmp_path)

    assert code == "7372"
    assert desc == "SIC 7372 desc"


# --- cache + backoff --------------------------------------------------------


def test_cache_hit_makes_no_call(monkeypatch, tmp_path):
    # pre-seed the cache so fetch_submissions reads the file, not the network
    fp = tmp_path / f"submissions_{CIK:010d}.json"
    fp.write_text(json.dumps(_submissions([("SC 13D", "2020-01-01", "X")])))
    calls = _no_network(monkeypatch, {})  # empty map -> any call raises

    df = stakes_13d.filings_13d(CIK, cache_dir=tmp_path)

    assert calls == []  # cache hit, no HTTP
    assert list(df["accession"]) == ["X"]


def test_backoff_retries_then_succeeds(monkeypatch, tmp_path):
    sleeps: list[float] = []
    payload = _submissions([("SC 13D", "2020-01-01", "X")])

    state = {"n": 0}

    def flaky(url, headers=None, timeout=None):
        state["n"] += 1
        if state["n"] < 3:
            raise requests.ConnectionError("SSL: UNEXPECTED_EOF_WHILE_READING")
        return _Resp(payload)

    monkeypatch.setattr(requests, "get", flaky)
    _install_policy(monkeypatch, sleeps)

    sub = stakes_13d.fetch_submissions(CIK, cache_dir=tmp_path)

    assert sub == payload
    assert state["n"] == 3            # 2 failures then success
    assert sleeps == [4.0, 8.0]


def test_filings_13d_empty_is_safe(monkeypatch, tmp_path):
    url = stakes_13d._SUBMISSIONS_URL.format(cik=CIK)
    _no_network(monkeypatch, {url: _submissions([])})
    df = stakes_13d.filings_13d(CIK, cache_dir=tmp_path)
    assert df.empty
    assert list(df.columns) == ["form", "filing_date", "accession", "primary_doc"]


def test_permanent_4xx_fails_fast_without_retry(monkeypatch, tmp_path):
    """A permanent 4xx (e.g. a 404 on an invalid CIK) must raise immediately
    without burning the 4 exp-backoff retries (which are for transient SSL/5xx)."""
    sleeps: list[float] = []
    calls = {"n": 0}

    def fake(url, headers=None, timeout=None):
        calls["n"] += 1
        return _Resp(None, status_code=404)

    monkeypatch.setattr(requests, "get", fake)
    _install_policy(monkeypatch, sleeps)

    with pytest.raises(RuntimeError, match="404"):
        stakes_13d.fetch_submissions(CIK, cache_dir=tmp_path)
    assert calls["n"] == 1  # no retry on a permanent client error
    assert sleeps == []


def test_server_5xx_is_retried(monkeypatch, tmp_path):
    """A transient 5xx is retried (then succeeds) -- not treated as permanent."""
    sleeps: list[float] = []
    state = {"n": 0}
    payload = _submissions([("SC 13D", "2020-01-01", "X")])

    def flaky(url, headers=None, timeout=None):
        state["n"] += 1
        return _Resp(payload, status_code=503 if state["n"] < 2 else 200)

    monkeypatch.setattr(requests, "get", flaky)
    _install_policy(monkeypatch, sleeps)

    df = stakes_13d.filings_13d(CIK, cache_dir=tmp_path)

    assert state["n"] == 2          # 1 retry (503) then success (200)
    assert sleeps == [4.0]
    assert list(df["accession"]) == ["X"]
