"""13D efts self-filing filter — hermetic (no network).

Pins :mod:`aionis.ingest.stakes_13d_efts`: the filer CIK is resolved from the
efts ``ciks[]`` array independent of array ORDER (the live probe showed the
issuer sits at index 0 for some issuers, index 1 for others); self-filings
(``filer_cik == issuer_cik``) are dropped; the verified query carries a 10-digit
zero-padded CIK + the root form ``SC 13D``; cache hits make no call; a permanent
4xx fails fast; transient 5xx / SSL retries with backoff; and ``from=`` paginates
issuers with >100 hits. Mirrors the offline pattern of ``test_stakes_13d``.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest
import requests

from aionis.ingest import stakes_13d_efts

ISSUER = 320193  # AAPL
FILER = 1234567
START, END = "2018-01-01", "2018-12-31"


class _Resp:
    def __init__(self, payload, status_code=200):
        self._p = payload
        self.status_code = status_code

    def json(self): return self._p


def _hit(ciks, adsh, date, form="SC 13D"):
    """One efts hit shaped like the verified live response."""
    return {"_index": "edgar", "_id": adsh, "_score": 1.0, "_source": {
        "ciks": ciks, "adsh": adsh, "file_date": date, "form": form,
        "display_names": [f"name-{c}" for c in ciks], "root_forms": ["SC 13D"],
    }}


def _efts(hits, total=None):
    n = total if total is not None else len(hits)
    return {"took": 1, "timed_out": False, "_shards": {}, "hits": {
        "total": {"value": n, "relation": "eq"}, "hits": hits,
    }}


def _no_network(monkeypatch, url_map, sleeps=None):
    """Patch requests.get to serve url_map; patch time.sleep to record (no waits)."""
    calls: list[str] = []

    def fake(url, headers=None, timeout=None):
        calls.append(url)
        if url in url_map:
            return _Resp(url_map[url])
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(requests, "get", fake)
    monkeypatch.setattr(stakes_13d_efts.time, "sleep",
                        lambda s: sleeps.append(s) if sleeps is not None else None)
    return calls


def _fetch(cache_dir):
    """Standard fetch (ISSUER over [START, END]) — DRY over the repeated call
    sites; the full arg list lives in one place."""
    return stakes_13d_efts.fetch_13d_filings_with_filer(
        ISSUER, start=START, end=END, cache_dir=cache_dir,
    )


# --- filer extraction (order-independent) ----------------------------------


def test_fetch_resolves_filer_independent_of_ciks_order(monkeypatch, tmp_path):
    """The issuer may sit at index 0 OR index 1 of ``ciks[]`` (live probe: CACC
    idx 0, BAC idx 1). The filer is the named CIK that is NOT the issuer — so
    both orderings must yield the same filer_cik."""
    url = stakes_13d_efts._efts_url(ISSUER, START, END, 0)
    hits = [
        _hit([f"{FILER:010d}", f"{ISSUER:010d}"], "A-filer-first", "2018-03-01"),
        _hit([f"{ISSUER:010d}", f"{FILER:010d}"], "B-issuer-first", "2018-04-01"),
    ]
    _no_network(monkeypatch, {url: _efts(hits)})

    df = _fetch(tmp_path)

    assert list(df["filer_cik"]) == [FILER, FILER]
    assert list(df["issuer_cik"]) == [ISSUER, ISSUER]
    assert df["filing_date"].is_monotonic_increasing


# --- self-filing drop -------------------------------------------------------


def test_filter_external_drops_self_filings(monkeypatch, tmp_path):
    """A filing whose only named CIK is the issuer is a self-filing (banks file
    SC 13D on their own stock); filter_external_13d must drop it and keep the
    external filer."""
    url = stakes_13d_efts._efts_url(ISSUER, START, END, 0)
    hits = [
        _hit([f"{FILER:010d}", f"{ISSUER:010d}"], "EXT", "2018-03-01"),   # external
        _hit([f"{ISSUER:010d}"], "SELF", "2018-05-01"),                   # self-filing
    ]
    _no_network(monkeypatch, {url: _efts(hits)})
    df = _fetch(tmp_path)

    ext = stakes_13d_efts.filter_external_13d(df)

    assert list(ext["accession"]) == ["EXT"]            # self-filing dropped
    assert list(df["accession"]) == ["EXT", "SELF"]     # input unchanged


def test_filter_external_does_not_mutate_input(monkeypatch, tmp_path):
    url = stakes_13d_efts._efts_url(ISSUER, START, END, 0)
    hits = [_hit([f"{ISSUER:010d}"], "SELF", "2018-05-01")]
    _no_network(monkeypatch, {url: _efts(hits)})
    df = _fetch(tmp_path)
    before = df.copy()

    stakes_13d_efts.filter_external_13d(df)

    pd.testing.assert_frame_equal(df, before)   # input not mutated


def test_external_13d_events_drops_self_in_one_call(monkeypatch, tmp_path):
    url = stakes_13d_efts._efts_url(ISSUER, START, END, 0)
    hits = [
        _hit([f"{FILER:010d}", f"{ISSUER:010d}"], "EXT", "2018-03-01"),
        _hit([f"{ISSUER:010d}"], "SELF", "2018-05-01"),
    ]
    _no_network(monkeypatch, {url: _efts(hits)})

    df = stakes_13d_efts.external_13d_events(ISSUER, start=START, end=END, cache_dir=tmp_path)

    assert list(df["accession"]) == ["EXT"]
    assert (df["filer_cik"] != df["issuer_cik"]).all()


# --- verified query shape ---------------------------------------------------


def test_url_carries_zero_padded_cik_and_root_form():
    """Pin the verified efts query: 10-digit zero-padded CIK, root form
    ``SC 13D`` (NOT the comma list that drops originals), custom date range."""
    url = stakes_13d_efts._efts_url(ISSUER, START, END, 0)
    assert "ciks=0000320193" in url          # 10-digit zero-padded (plain -> 0 hits)
    assert "forms=SC%2013D" in url            # root form; expands to SC 13D/A
    assert "dateRange=custom" in url
    assert f"startdt={START}" in url and f"enddt={END}" in url
    assert "from=0" in url


# --- date range (defense-in-depth; efts bounds server-side) -----------------


def test_date_range_filters_out_of_window_hit(monkeypatch, tmp_path):
    url = stakes_13d_efts._efts_url(ISSUER, START, END, 0)
    hits = [
        _hit([f"{FILER:010d}", f"{ISSUER:010d}"], "PRE", "2015-01-01"),  # before start
        _hit([f"{FILER:010d}", f"{ISSUER:010d}"], "IN", "2018-06-01"),   # in window
        _hit([f"{FILER:010d}", f"{ISSUER:010d}"], "POST", "2027-01-01"),  # after end
    ]
    calls = _no_network(monkeypatch, {url: _efts(hits)})

    df = _fetch(tmp_path)

    assert list(df["accession"]) == ["IN"]
    assert any(f"startdt={START}" in c and f"enddt={END}" in c for c in calls)  # bounded request


# --- pagination across from= pages ------------------------------------------


def test_paginates_across_from_pages(monkeypatch, tmp_path):
    """Issuers with >100 hits are paginated via ``from=`` (verified: BAC 2016–2024
    = 287, recovered across from=0/100/200). Here _PAGE_SIZE is shrunk to 2 so a
    3-hit response exercises the from=0 -> from=2 walk hermetically."""
    monkeypatch.setattr(stakes_13d_efts, "_PAGE_SIZE", 2)
    hits = [
        _hit([f"{FILER:010d}", f"{ISSUER:010d}"], "A", "2018-01-10"),
        _hit([f"{FILER:010d}", f"{ISSUER:010d}"], "B", "2018-02-10"),
        _hit([f"{FILER:010d}", f"{ISSUER:010d}"], "C", "2018-03-10"),
    ]
    url_map = {
        stakes_13d_efts._efts_url(ISSUER, START, END, 0): _efts(hits[0:2], total=3),
        stakes_13d_efts._efts_url(ISSUER, START, END, 2): _efts(hits[2:3], total=3),
    }
    calls = _no_network(monkeypatch, url_map)

    df = _fetch(tmp_path)

    assert set(df["accession"]) == {"A", "B", "C"}
    assert len(df) == 3
    # both pages fetched, in order
    assert stakes_13d_efts._efts_url(ISSUER, START, END, 0) in calls
    assert stakes_13d_efts._efts_url(ISSUER, START, END, 2) in calls


# --- cache + backoff --------------------------------------------------------


def test_cache_hit_makes_no_call(monkeypatch, tmp_path):
    # pre-seed the assembled-hit-list cache (the format _fetch_efts_hits writes)
    fp = tmp_path / f"efts_13d_{ISSUER:010d}_{START}_{END}.json"
    sources = [_hit([f"{FILER:010d}", f"{ISSUER:010d}"], "CACHED", "2018-04-01")["_source"]]
    fp.write_text(json.dumps(sources))
    _no_network(monkeypatch, {})  # empty map -> any call raises

    df = _fetch(tmp_path)

    assert list(df["accession"]) == ["CACHED"]


def test_backoff_retries_then_succeeds(monkeypatch, tmp_path):
    sleeps: list[float] = []
    payload = _efts([_hit([f"{FILER:010d}", f"{ISSUER:010d}"], "X", "2018-01-01")])
    state = {"n": 0}

    def flaky(url, headers=None, timeout=None):
        state["n"] += 1
        if state["n"] < 3:
            raise requests.ConnectionError("SSL: UNEXPECTED_EOF_WHILE_READING")
        return _Resp(payload)

    monkeypatch.setattr(requests, "get", flaky)
    monkeypatch.setattr(stakes_13d_efts.time, "sleep", lambda s: sleeps.append(s))

    df = _fetch(tmp_path)

    assert list(df["accession"]) == ["X"]
    assert state["n"] == 3                 # 2 failures then success
    # backoff (4*1, 4*2) between retries, then the 0.15s fair-access pause on success
    assert sleeps == [4, 8, 0.15]


def test_server_5xx_is_retried(monkeypatch, tmp_path):
    """A transient 5xx is retried (then succeeds) -- not treated as permanent."""
    sleeps: list[float] = []
    state = {"n": 0}
    payload = _efts([_hit([f"{FILER:010d}", f"{ISSUER:010d}"], "X", "2018-01-01")])

    def flaky(url, headers=None, timeout=None):
        state["n"] += 1
        return _Resp(payload, status_code=503 if state["n"] < 2 else 200)

    monkeypatch.setattr(requests, "get", flaky)
    monkeypatch.setattr(stakes_13d_efts.time, "sleep", lambda s: sleeps.append(s))

    df = _fetch(tmp_path)

    assert state["n"] == 2
    assert sleeps == [4, 0.15]
    assert list(df["accession"]) == ["X"]


def test_permanent_4xx_fails_fast_without_retry(monkeypatch, tmp_path):
    """A permanent 4xx must raise immediately without burning the backoff retries."""
    sleeps: list[float] = []
    calls = {"n": 0}

    def fake(url, headers=None, timeout=None):
        calls["n"] += 1
        return _Resp(None, status_code=404)

    monkeypatch.setattr(requests, "get", fake)
    monkeypatch.setattr(stakes_13d_efts.time, "sleep", lambda s: sleeps.append(s))

    with pytest.raises(RuntimeError, match="404"):
        _fetch(tmp_path)
    assert calls["n"] == 1      # no retry on a permanent client error
    assert sleeps == []


# --- empty is safe ----------------------------------------------------------


def test_fetch_empty_is_safe(monkeypatch, tmp_path):
    url = stakes_13d_efts._efts_url(ISSUER, START, END, 0)
    _no_network(monkeypatch, {url: _efts([])})
    df = _fetch(tmp_path)
    assert df.empty
    assert list(df.columns) == ["issuer_cik", "filer_cik", "filing_date", "accession", "form"]
    # filter on an empty frame is a no-op (and does not mutate)
    assert stakes_13d_efts.filter_external_13d(df).empty
