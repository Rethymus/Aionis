"""Hermetic tests for the DFF ALFRED vintage ingest (RES-02).

Covers the PIT as-of construction: first-print-per-ref-date discipline,
strictly-before as-of join (a same-day 16:30 ET print is FUTURE information at
date d), one-day-conservative ΔDFF, the no-lookahead perturbation invariant
(future vintages never move past values), and the offline cache-hit fetch path.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import requests

from aionis.ingest.macro_dff import (
    dff_as_of_levels,
    dff_daily_changes,
    fetch_dff_vintages,
)

# --- fixture builders ----------------------------------------------------------


def _vint(ref: str | pd.Timestamp, pub: str | pd.Timestamp, value: float) -> dict:
    """One ALFRED observation row (FRED serializes values as strings)."""
    return {
        "date": pd.Timestamp(ref).strftime("%Y-%m-%d"),
        "realtime_start": pd.Timestamp(pub).strftime("%Y-%m-%d"),
        "value": str(value),
    }


def _frame(rows: list[dict]) -> pd.DataFrame:
    """Parse raw observation rows like fetch_alfred_vintages does."""
    return (
        pd.DataFrame(
            {
                "ref_date": pd.to_datetime([r["date"] for r in rows]),
                "realtime_start": pd.to_datetime([r["realtime_start"] for r in rows]),
                "value": pd.to_numeric([r["value"] for r in rows], errors="coerce"),
            }
        )
        .dropna(subset=["value"])
        .reset_index(drop=True)
    )


def _write_cache(cache_dir: Path, series_id: str, rows: list[dict]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"alfred_{series_id}.json").write_text(json.dumps({"observations": rows}))


def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("network call attempted in offline test")

    monkeypatch.setattr(requests, "get", _boom)


def _biz_days(start: str, n: int) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.bdate_range(start, periods=n)).normalize()


# --- strictly-before as-of join -------------------------------------------------


def test_as_of_level_is_first_print_strictly_before_date() -> None:
    # DFF publishes same-day (realtime_start == ref_date) plus one revision per
    # ref date next day (must lose to the first print).
    days = _biz_days("2024-01-01", 4)  # d0..d3
    rows = [
        _vint(days[0], days[0], 0.08),
        _vint(days[1], days[1], 0.10),
        _vint(days[1], days[1] + pd.Timedelta(days=1), 0.09),  # revision: loses
        _vint(days[2], days[2], 0.12),
        _vint(days[3], days[3], 0.11),
    ]
    vintages = _frame(rows)

    levels = dff_as_of_levels(days, vintages)

    # level(d) = latest first print strictly before d; d's own same-day print
    # (16:30 ET) is future information at d.
    assert np.isnan(levels.iloc[0])  # nothing strictly before d0
    assert levels.iloc[1] == pytest.approx(0.08)  # d0's print, NOT d1's 0.10
    assert levels.iloc[2] == pytest.approx(0.10)  # first print of d1 (0.09 revision lost)
    assert levels.iloc[3] == pytest.approx(0.12)  # first print of d2


def test_first_print_beats_same_ref_date_revision() -> None:
    days = _biz_days("2024-02-01", 2)
    rows = [
        _vint(days[0], days[0], 0.05),
        _vint(days[1], days[1], 0.07),
        _vint(days[1], days[1] + pd.Timedelta(days=1), 0.08),
        _vint(days[1], days[1] + pd.Timedelta(days=2), 0.081),  # later revision
    ]
    levels = dff_as_of_levels(_biz_days("2024-02-01", 3), _frame(rows))
    assert levels.iloc[2] == pytest.approx(0.07)  # first print, not revisions


def test_dff_changes_is_first_difference_of_as_of_levels() -> None:
    days = _biz_days("2024-03-01", 5)
    rows = [_vint(days[i], days[i], 0.05 + 0.01 * i) for i in range(4)]
    vintages = _frame(rows)

    changes = dff_daily_changes(days, vintages)

    assert changes.name == "dff_change"
    assert np.isnan(changes.iloc[0])  # no level yet
    assert np.isnan(changes.iloc[1])  # level(d1) is NaN -> change undefined
    assert changes.iloc[2] == pytest.approx(0.06 - 0.05)  # level(d2) - level(d1)
    assert changes.iloc[3] == pytest.approx(0.07 - 0.06)
    assert changes.iloc[4] == pytest.approx(0.08 - 0.07)


# --- THE no-lookahead invariant --------------------------------------------------


def test_future_vintages_never_move_past_as_of_values() -> None:
    """Perturbing every value first published at/after a cutoff must not move
    the as-of levels at dates <= cutoff (same discipline as the macro-surprise
    no-lookahead test)."""
    days = _biz_days("2024-04-01", 12)
    rows = [_vint(days[i], days[i], 0.04 + 0.005 * i) for i in range(10)]
    base = dff_as_of_levels(days, _frame(rows))

    cutoff = days[6]
    perturbed = [
        dict(r, value=str(float(r["value"]) * 3.0 + 7.0))
        if pd.Timestamp(r["realtime_start"]) >= cutoff
        else r
        for r in rows
    ]
    got = dff_as_of_levels(days, _frame(perturbed))

    # level(d) uses only prints strictly before d: through d6 (which uses the
    # unperturbed d5 print) everything is invariant; the first date that can
    # respond is d7, whose level uses the perturbed d6 print.
    pd.testing.assert_series_equal(got.iloc[:7], base.iloc[:7])
    assert got.iloc[7] != base.iloc[7]
    assert got.iloc[7] == pytest.approx(3.0 * base.iloc[7] + 7.0)


def test_same_day_revision_cannot_enter_current_level() -> None:
    """A revision republished ON date d (realtime_start == d) must not change
    level(d) — it is strictly-before excluded (the macro_surprise prior rule)."""
    days = _biz_days("2024-05-01", 3)
    rows = [
        _vint(days[0], days[0], 0.03),
        _vint(days[1], days[1], 0.05),
        _vint(days[0], days[2], 0.99),  # poison revision of d0 published at d2
        _vint(days[2], days[2], 0.06),
    ]
    levels = dff_as_of_levels(days, _frame(rows))
    assert levels.iloc[2] == pytest.approx(0.05)  # first print of d1, not the poison
    assert levels.iloc[1] == pytest.approx(0.03)


# --- offline cache-hit fetch path ------------------------------------------------


def test_fetch_dff_vintages_cache_hit_is_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_network(monkeypatch)
    days = _biz_days("2024-06-01", 3)
    _write_cache(tmp_path, "DFF", [_vint(days[0], days[0], 0.05)])

    vintages = fetch_dff_vintages(fred_api_key="offline", cache_dir=tmp_path)

    assert list(vintages.columns) == ["ref_date", "realtime_start", "value"]
    assert len(vintages) == 1
    assert vintages["value"].iloc[0] == pytest.approx(0.05)


def test_fetch_dff_vintages_missing_value_rows_are_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_network(monkeypatch)
    _write_cache(
        tmp_path,
        "DFF",
        [_vint("2024-06-03", "2024-06-03", 0.05), _vint("2024-06-04", "2024-06-04", 0.0)],
    )
    rows = json.loads((tmp_path / "alfred_DFF.json").read_text())["observations"]
    rows.append(_vint("2024-06-05", "2024-06-05", "."))  # "." parses to NaN, dropped
    (tmp_path / "alfred_DFF.json").write_text(json.dumps({"observations": rows}))

    vintages = fetch_dff_vintages("offline", tmp_path)
    assert len(vintages) == 2


def test_as_of_dates_beyond_vintages_stay_nan_until_knowable() -> None:
    days = _biz_days("2024-07-01", 5)
    rows = [_vint(days[0], days[0], 0.02), _vint(days[1], days[1], 0.03)]
    levels = dff_as_of_levels(days, _frame(rows))
    assert np.isnan(levels.iloc[0])
    assert levels.iloc[1] == pytest.approx(0.02)
    # carries the last knowable level forward
    assert np.allclose(levels.iloc[2:].to_numpy(), [0.03, 0.03, 0.03])
