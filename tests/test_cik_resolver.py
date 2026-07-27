"""CIK resolver invariants — hermetic (no network).

Pins normalization (FB->FB, BRK.B/BRK/B->BRK-B), the pure SEC-snapshot parser,
cache hit / miss / force semantics, and the rule that unresolved tickers are
simply absent (never an error). Mirrors ``test_fundamentals.py``: synthetic
fixtures only; the loader's network path is exercised separately and logged.
"""
from __future__ import annotations

import json

from aionis.ingest import cik_resolver as mod
from aionis.ingest.cik_resolver import _parse_sec_tickers, resolve_ciks

# Synthetic SEC company_tickers.json raw payload (the loader's network input).
_RAW_SEC = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 1326801, "ticker": "META", "title": "Meta Platforms, Inc."},
    "2": {"cik_str": 58492, "ticker": "BRK-B", "title": "Berkshire Hathaway"},
    "3": {"cik_str": 1780302, "ticker": "BF-B", "title": "Brown-Forman"},
}


def _seed_cache(tmp_path, mapping: dict) -> None:
    (tmp_path / mod._CACHE_NAME).write_text(json.dumps(mapping))


def test_parse_sec_tickers_normalizes_keys() -> None:
    # SEC's '-' share-class form is preserved; keys are upper-cased.
    m = _parse_sec_tickers(_RAW_SEC)
    assert m["AAPL"] == 320193
    assert m["META"] == 1326801
    assert m["BRK-B"] == 58492
    assert m["BF-B"] == 1780302


def test_parse_sec_tickers_canonicalizes_separators() -> None:
    # A dotted/slash raw ticker from the SEC field collapses to '-' via normalize.
    m = _parse_sec_tickers({"0": {"cik_str": 1, "ticker": "brk.b"}})
    assert m == {"BRK-B": 1}
    m2 = _parse_sec_tickers({"0": {"cik_str": 2, "ticker": " a/b "}})
    assert m2 == {"A-B": 2}


def test_parse_sec_tickers_skips_malformed_rows() -> None:
    raw = {
        "0": {"cik_str": 320193, "ticker": "AAPL"},
        "1": {"cik_str": None, "ticker": "X"},   # no CIK -> skipped
        "2": {"cik_str": 5, "ticker": ""},        # empty ticker -> skipped
        "3": "not-a-dict",                        # wrong shape -> skipped
    }
    assert _parse_sec_tickers(raw) == {"AAPL": 320193}


def test_resolve_normalizes_input_and_share_class(tmp_path) -> None:
    _seed_cache(tmp_path, {"AAPL": 320193, "BRK-B": 58492, "BF-B": 1780302,
                           "META": 1326801})
    # lower-case, dotted, and slashed inputs all canonicalize to the same key.
    out = resolve_ciks(["aapl", "BRK.B", "BRK/B", "bf-b", "meta"], cache_dir=tmp_path)
    assert out == {"AAPL": 320193, "BRK-B": 58492, "BF-B": 1780302, "META": 1326801}


def test_resolve_historical_ticker_kept_as_is(tmp_path) -> None:
    # FB is a HISTORICAL ticker; it must NOT be remapped to META by normalization
    # (no ad-hoc rename). If FB were in the snapshot it resolves verbatim.
    _seed_cache(tmp_path, {"FB": 1326801, "AAPL": 320193})
    out = resolve_ciks(["FB", "AAPL"], cache_dir=tmp_path)
    assert out == {"FB": 1326801, "AAPL": 320193}


def test_resolve_bankruptcy_suffix_preserved(tmp_path) -> None:
    # The 'Q' bankruptcy suffix is real identity, not formatting noise; it is kept.
    _seed_cache(tmp_path, {"EKDKQ": 1165})
    assert resolve_ciks(["ekdkq"], cache_dir=tmp_path) == {"EKDKQ": 1165}


def test_resolve_unresolved_absent_not_error(tmp_path) -> None:
    # FB / EKDKQ are absent from the current snapshot; ZZZZ never existed.
    # All three are simply omitted — resolve_ciks NEVER raises on a miss.
    _seed_cache(tmp_path, {"AAPL": 320193})
    out = resolve_ciks(["AAPL", "FB", "EKDKQ", "ZZZZZ"], cache_dir=tmp_path)
    assert out == {"AAPL": 320193}


def test_resolve_empty_input(tmp_path) -> None:
    _seed_cache(tmp_path, {"AAPL": 320193})
    assert resolve_ciks([], cache_dir=tmp_path) == {}


def test_resolve_dedups_repeated_input(tmp_path) -> None:
    _seed_cache(tmp_path, {"AAPL": 320193})
    out = resolve_ciks(["aapl", "AAPL", "BRK.B"], cache_dir=tmp_path)
    assert out == {"AAPL": 320193}


def test_cache_hit_makes_no_network_call(tmp_path, monkeypatch) -> None:
    _seed_cache(tmp_path, {"AAPL": 320193})

    def boom(url: str) -> dict:
        raise AssertionError(f"should not fetch on cache hit, called {url}")

    monkeypatch.setattr(mod, "_fetch_with_backoff", boom)
    assert resolve_ciks(["AAPL"], cache_dir=tmp_path) == {"AAPL": 320193}


def test_force_bypasses_cache_and_rewrites(tmp_path, monkeypatch) -> None:
    # A stale cache exists; force=True must re-fetch (mocked) and overwrite it.
    _seed_cache(tmp_path, {"STALE": 1})
    monkeypatch.setattr(mod, "_fetch_with_backoff", lambda url: _RAW_SEC)
    # Request STALE (gone post-refresh) + the fresh tickers; only fresh resolve.
    out = resolve_ciks(["STALE", "AAPL", "META", "BRK-B", "BF-B"],
                       cache_dir=tmp_path, force=True)
    assert out == {"AAPL": 320193, "META": 1326801, "BRK-B": 58492, "BF-B": 1780302}
    # cache file was rewritten with the fresh normalized snapshot (STALE gone).
    fresh = json.loads((tmp_path / mod._CACHE_NAME).read_text())
    assert fresh["AAPL"] == 320193 and "STALE" not in fresh
