"""Hermetic tests for scripts/e3_extend_prices.py --through (round 242).

The row-extension helper is tested in isolation with an injected fetcher
and session calendar — no network, no frozen-file writes.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "e3_extend_prices.py"
sys.path.insert(0, str(ROOT / "scripts"))


def _load():
    spec = importlib.util.spec_from_file_location("e3_extend_prices", SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture()
def ext(monkeypatch):
    m = _load()
    sessions = pd.bdate_range("2026-08-03", "2026-09-30")  # business-day stand-in
    monkeypatch.setattr(m, "nyse_sessions",
                        lambda start, end: pd.DatetimeIndex(
                            [d for d in sessions if start <= d <= end]))
    return m


def _toy_px() -> pd.DataFrame:
    idx = pd.bdate_range("2026-07-27", "2026-08-31")
    return pd.DataFrame({"AAA": 10.0, "BBB": 20.0}, index=idx)


def test_rows_extended_on_session_grid(ext) -> None:
    calls = {}

    def fake_fetch(tickers, start, end):
        calls["tickers"], calls["start"], calls["end"] = tickers, start, end
        grid = pd.bdate_range(start, end)
        return {t: pd.Series([float(i + 1) for i in range(len(grid))], index=grid)
                for t in tickers}

    px = _toy_px()
    out = ext._extend_rows_through(px, pd.Timestamp("2026-09-30"), fetch=fake_fetch)
    assert pd.Timestamp(out.index.max()) == pd.Timestamp("2026-09-30")
    assert pd.Timestamp(out.index.min()) == px.index.min()
    # only NEW sessions appended; the original rows are untouched values
    assert (out.loc[px.index, "AAA"] == px["AAA"]).all()
    # the fetcher received every panel ticker with the post-edge window
    assert set(calls["tickers"]) == {"AAA", "BBB"}
    assert calls["start"] == "2026-09-01"


def test_input_frame_never_mutated(ext) -> None:
    px = _toy_px()
    before = px.copy()

    def fake_fetch(tickers, start, end):
        grid = pd.bdate_range(start, end)
        return {t: pd.Series(1.0, index=grid) for t in tickers}

    ext._extend_rows_through(px, pd.Timestamp("2026-09-30"), fetch=fake_fetch)
    pd.testing.assert_frame_equal(px, before)


def test_through_at_or_before_edge_rejected(ext) -> None:
    px = _toy_px()
    with pytest.raises(SystemExit, match="AFTER the panel edge"):
        ext._extend_rows_through(px, pd.Timestamp("2026-08-31"), fetch=None)
    with pytest.raises(SystemExit):
        ext._extend_rows_through(px, pd.Timestamp("2026-07-01"), fetch=None)


def test_no_sessions_after_edge_rejected(ext) -> None:
    # edge AT the fixture calendar's end; the window (edge+1 .. target)
    # contains zero calendar sessions -> guard fires
    px = _toy_px()
    px = px.loc[:pd.Timestamp("2026-09-30")]
    px = px.reindex(px.index.union([pd.Timestamp("2026-09-30")]))
    with pytest.raises(SystemExit, match="no NYSE sessions"):
        ext._extend_rows_through(px, pd.Timestamp("2026-10-01"),
                                 fetch=lambda *a, **k: {})
