"""fetch_event_text: URL construction, cleaning/truncation, disk cache, stub fallback.

Offline — monkeypatches ``requests.get`` so no network is touched.
AAA pattern, matches existing repo test style.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import requests

from aionis.ingest import event_text
from aionis.ingest.event_text import _build_url, _clean, fetch_event_text


class _FakeResp:
    """Minimal stand-in for requests.Response."""

    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"status {self.status_code}")


def _make_events(*rows: tuple[str, str, str]) -> pd.DataFrame:
    """Build a minimal events frame: (event_id, event_type, event_ts YYYY-MM-DD HH:MM)."""
    return pd.DataFrame(
        [
            {"event_id": eid, "event_type": et, "event_ts": pd.Timestamp(ts)}
            for eid, et, ts in rows
        ]
    )


# --- URL construction -------------------------------------------------------


@pytest.mark.parametrize(
    "event_type,ts,expected",
    [
        (
            "FOMC",
            "2023-03-22 14:00",
            "https://www.federalreserve.gov/newsevents/pressreleases/monetary20230322a.htm",
        ),
        (
            "CPI",
            "2024-03-12 08:30",
            "https://www.bls.gov/news.release/archives/cpi_03122024.htm",
        ),
        (
            "NFP",
            "2023-01-06 08:30",
            "https://www.bls.gov/news.release/archives/empsit_01062023.htm",
        ),
    ],
)
def test_url_construction_for_each_event_type(event_type: str, ts: str, expected: str) -> None:
    # Arrange / Act
    url = _build_url(event_type, pd.Timestamp(ts))
    # Assert
    assert url == expected


def test_build_url_unknown_type_raises() -> None:
    # Arrange / Act / Assert
    with pytest.raises(ValueError):
        _build_url("GDP", pd.Timestamp("2024-01-01"))


# --- Cleaning + truncation --------------------------------------------------


def test_clean_strips_to_bls_boilerplate_marker_and_truncates() -> None:
    # Arrange — BLS pages start with a "Transmission of material..." embargo notice.
    boilerplate = (
        "Transmission of material in this release is embargoed "
        "until USDL-24-0321-CPI. "
    )
    body = "Consumer Price Index Summary " + ("x" * 5000)
    html = f"<html><body>{boilerplate}{body}</body></html>"

    # Act
    out = _clean(html, "CPI")

    # Assert — body starts at the marker, hard-capped at 4000 chars.
    assert out.startswith("Transmission of material")
    assert "Consumer Price Index Summary" in out
    assert len(out) == 4000


def test_clean_strips_to_fomc_release_marker() -> None:
    # Arrange
    html = "<html><body>Nav bar junk. For immediate release The Federal Reserve...</body></html>"

    # Act
    out = _clean(html, "FOMC")

    # Assert
    assert out.startswith("For immediate release")
    assert "Nav bar junk" not in out


def test_clean_without_marker_truncates_full_text() -> None:
    # Arrange — no marker present, should still truncate.
    html = "<p>" + ("a" * 5000) + "</p>"

    # Act
    out = _clean(html, "FOMC")

    # Assert
    assert len(out) == 4000


# --- Cache round-trip -------------------------------------------------------


def test_cache_roundtrip_first_call_writes_second_call_reads(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange
    events = _make_events(
        ("FOMC_20240320", "FOMC", "2024-03-20 14:00"),
    )
    calls = {"n": 0}

    def fake_get(url: str, **_: Any) -> _FakeResp:
        calls["n"] += 1
        return _FakeResp(f"<p>body for {url}</p>")

    monkeypatch.setattr(event_text.requests, "get", fake_get)
    monkeypatch.setattr(event_text, "_policy_get", fake_get)
    cache = tmp_path / "cache"

    # Act — first pass: the event misses cache and hits HTTP.
    out1 = fetch_event_text(events, cache_dir=cache)

    # Assert — one fetch per event, files written, content cleaned.
    assert calls["n"] == 1
    assert (cache / "FOMC_20240320.txt").exists()
    assert len(out1) == 1
    assert all("body for" in t for t in out1["text"].tolist())

    # Act — second pass: all cache hits, no HTTP, identical content.
    calls["n"] = 0
    out2 = fetch_event_text(events, cache_dir=cache)
    assert calls["n"] == 0
    assert out1["text"].tolist() == out2["text"].tolist()


# --- Stub fallback ----------------------------------------------------------


def test_stub_fallback_on_connection_error_is_not_cached(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange — every HTTP attempt fails with a connection error.
    events = _make_events(("FOMC_20240320", "FOMC", "2024-03-20 14:00"))

    def fake_get(url: str, **_: Any) -> _FakeResp:
        raise requests.exceptions.ConnectionError(f"blocked {url}")

    monkeypatch.setattr(event_text.requests, "get", fake_get)
    monkeypatch.setattr(event_text, "_policy_get", lambda *_, **__: fake_get(""))
    cache = tmp_path / "cache"

    # Act
    out = fetch_event_text(events, cache_dir=cache)

    # Assert — outcome-free stub returned, NOT written to cache (so we can retry).
    assert len(out) == 1
    assert "Structural description only" in out.iloc[0]["text"]
    assert not (cache / "FOMC_20240320.txt").exists()


def test_stub_fallback_on_404_is_not_cached(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange — BLS/Fed returns 404 for an unknown archive date.
    events = _make_events(("FOMC_20240320", "FOMC", "2024-03-20 14:00"))

    def fake_get(url: str, **_: Any) -> _FakeResp:
        return _FakeResp("not found", status_code=404)

    monkeypatch.setattr(event_text.requests, "get", fake_get)
    monkeypatch.setattr(event_text, "_policy_get", lambda *_, **__: fake_get(""))
    cache = tmp_path / "cache"

    # Act
    out = fetch_event_text(events, cache_dir=cache)

    # Assert
    assert "Structural description only" in out.iloc[0]["text"]
    assert not (cache / "FOMC_20240320.txt").exists()


def test_default_cache_dir_used_when_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange — point settings.data_dir at tmp_path so the default cache lives there.
    monkeypatch.setattr(event_text.settings, "data_dir", tmp_path)
    events = _make_events(("FOMC_20240320", "FOMC", "2024-03-20 14:00"))

    def fake_get(url: str, **_: Any) -> _FakeResp:
        return _FakeResp("<p>hi</p>")

    monkeypatch.setattr(event_text.requests, "get", fake_get)
    monkeypatch.setattr(event_text, "_policy_get", lambda *_, **__: fake_get(""))

    # Act
    fetch_event_text(events, cache_dir=None)

    # Assert — default path data/cache/event_text was created and written.
    assert (tmp_path / "cache" / "event_text" / "FOMC_20240320.txt").exists()


@pytest.mark.parametrize("event_type", ["CPI", "NFP"])
def test_bls_blocked(event_type: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Blocked BLS event types must not make a live request on a cache miss."""
    monkeypatch.setattr(
        event_text.requests,
        "get",
        lambda *_, **__: pytest.fail("BLS cache miss attempted an HTTP request"),
    )

    with pytest.raises(RuntimeError, match="BLS is blocked"):
        event_text._fetch_text(event_type, pd.Timestamp("2024-03-12 08:30"))


# --- EDGAR primary-document branch (arm_e13 LLM-edge input) ------------------


def _make_edgar_events(*rows: tuple[str, int, str, str]) -> pd.DataFrame:
    """Build an EDGAR events frame: (event_id, cik, accession, primary_doc)."""
    return pd.DataFrame(
        [
            {"event_id": eid, "cik": cik, "accession": accn, "primary_doc": doc}
            for eid, cik, accn, doc in rows
        ]
    )


def test_edgar_primary_text_fetches_canonical_url_and_caches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """First call hits the canonical EDGAR archive URL; second call is cache-only."""
    events = _make_edgar_events(
        ("T0:0000001098-24-000010", 1098, "0000001098-24-000010", "d.htm"),
    )
    urls: list[str] = []

    def fake_get(url: str, **_: Any) -> _FakeResp:
        urls.append(url)
        return _FakeResp("<p>Acquiror intends to acquire 6.2% of the shares.</p>")

    monkeypatch.setattr(event_text, "_policy_get", fake_get)
    cache = tmp_path / "cache"

    out1 = event_text.fetch_edgar_primary_text(events, cache_dir=cache)
    # canonical archive pattern: dashes stripped from the accession
    assert urls == [
        "https://www.sec.gov/Archives/edgar/data/1098/000000109824000010/d.htm"
    ]
    assert "6.2% of the shares" in out1["text"].iloc[0]
    cache_name = cache / "edgar_000000109824000010__d.htm.txt"
    assert cache_name.exists()

    urls.clear()
    out2 = event_text.fetch_edgar_primary_text(events, cache_dir=cache)
    assert urls == []  # pure cache hit
    assert out1["text"].tolist() == out2["text"].tolist()


def test_edgar_primary_text_empty_doc_returns_empty_without_http(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Rows without a primary_doc filename (pre-column cache rows) skip HTTP."""
    events = _make_edgar_events(
        ("T0:old-1", 1098, "0000001098-24-000011", ""),
    )
    monkeypatch.setattr(
        event_text,
        "_policy_get",
        lambda *_, **__: pytest.fail("empty primary_doc attempted an HTTP request"),
    )
    out = event_text.fetch_edgar_primary_text(events, cache_dir=tmp_path / "cache")
    assert out["text"].tolist() == [""]


def test_edgar_primary_text_404_returns_empty_and_never_caches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A 404 (e.g. delisted/wrong doc) -> text="" so the LLM edge skips the
    event honestly; nothing is cached so a later run can retry."""
    events = _make_edgar_events(
        ("T0:gone-1", 1098, "0000001098-24-000012", "missing.htm"),
    )
    monkeypatch.setattr(event_text, "_policy_get", lambda *_, **__: _FakeResp("", status_code=404))
    cache = tmp_path / "cache"

    out = event_text.fetch_edgar_primary_text(events, cache_dir=cache)
    assert out["text"].tolist() == [""]
    assert not (cache / "edgar_000000109824000012__missing.htm.txt").exists()


def test_edgar_clean_does_not_marker_strip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """EDGAR cleaning must NOT apply FOMC/BLS marker stripping — a marker
    appearing mid-filing would silently discard content."""
    html = (
        "<p>Item 1. Identity and Background.</p>"
        "<p>for release to shareholders only after the record date.</p>"
        "<p>Item 4. Purpose of Transaction.</p>"
    )
    events = _make_edgar_events(
        ("T0:strip-1", 1098, "0000001098-24-000013", "doc.htm"),
    )
    monkeypatch.setattr(event_text, "_policy_get", lambda *_, **__: _FakeResp(html))
    out = event_text.fetch_edgar_primary_text(events, cache_dir=tmp_path / "cache")
    text = out["text"].iloc[0]
    assert text.startswith("Item 1. Identity and Background.")
    assert "Purpose of Transaction" in text
