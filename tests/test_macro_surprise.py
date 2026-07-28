"""Macro-surprise invariants — strictly-prior windows, first-print selection,
prior-vintage rule, event matching, and the fail-loud matching guard.

All fixtures are small hand-built ALFRED-shaped vintage archives (offline).
The critical test is the no-lookahead one: the expectation (and the z
denominator) at release r must be invariant to anything first published at or
after r — a single off-by-one there invalidates the experiment.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import requests

from aionis.features.macro_surprise import (
    Z_CLIP,
    build_surprise_features,
    fetch_alfred_vintages,
    first_print_changes,
    macro_surprise_date_broadcast,
    surprise_time_series,
)

ET = "America/New_York"


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


def _make_archive(
    n_months: int,
    kind: str,
    seed: int,
    start_ref: str = "2019-01-01",
    base: float = 100.0,
) -> tuple[list[dict], list[pd.Timestamp], list[pd.Timestamp]]:
    """ALFRED-shaped archive: monthly first prints (~13th of the next month)
    plus a small revision 14 days later (exercises the latest-vintage prior
    rule). Returns (rows, refs, pubs)."""
    rng = np.random.default_rng(seed)
    refs = [pd.Timestamp(t) for t in pd.date_range(start_ref, periods=n_months, freq="MS")]
    pubs = [r + pd.DateOffset(months=1, days=12) for r in refs]
    rows: list[dict] = []
    level = base
    for ref, pub in zip(refs, pubs, strict=True):
        step = 0.4 + 0.3 * float(rng.standard_normal())
        level = level * (1.0 + step / 100.0) if kind == "pct" else level + step * 100.0
        rows.append(_vint(ref, pub, round(level, 4)))
        rows.append(_vint(ref, pub + pd.Timedelta(days=14), round(level * 1.0005, 4)))
    return rows, refs, pubs


def _perturb(rows: list[dict], cutoff: pd.Timestamp, *, include_cutoff: bool) -> list[dict]:
    """New rows with every value first published at/after (or strictly after)
    ``cutoff`` grossly altered. Originals are not mutated."""
    out: list[dict] = []
    for r in rows:
        pub = pd.Timestamp(r["realtime_start"])
        hit = pub >= cutoff if include_cutoff else pub > cutoff
        out.append(dict(r, value=str(float(r["value"]) * 3.0 + 7.0)) if hit else dict(r))
    return out


def _write_cache(cache_dir: Path, series_id: str, rows: list[dict]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"alfred_{series_id}.json").write_text(json.dumps({"observations": rows}))


def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("network call attempted in offline test")

    monkeypatch.setattr(requests, "get", _boom)


def _events(specs: list[tuple[str, pd.Timestamp]]) -> pd.DataFrame:
    rows = []
    for event_type, day in specs:
        d = pd.Timestamp(day).normalize()
        if event_type == "FOMC":
            offset = pd.Timedelta(hours=14)
        else:
            offset = pd.Timedelta(hours=8, minutes=30)
        rows.append(
            {
                "event_id": f"{event_type}_{d:%Y%m%d}",
                "event_type": event_type,
                "event_ts": (d + offset).tz_localize(ET),
            }
        )
    return pd.DataFrame(rows)


# --- first-print selection + prior-vintage rule ---------------------------------


def test_first_print_is_min_realtime_start_per_reference_month() -> None:
    rows = [
        _vint("2019-12-01", "2020-01-14", 100.0),
        _vint("2020-01-01", "2020-02-13", 100.5),  # first print of Jan
        _vint("2020-01-01", "2020-03-11", 100.7),  # later revision must lose
    ]

    changes = first_print_changes(_frame(rows), "diff")

    jan = changes.loc[changes["ref_date"] == pd.Timestamp("2020-01-01")].iloc[0]
    assert jan["first_print"] == pytest.approx(100.5)
    assert jan["pub_date"] == pd.Timestamp("2020-02-13")
    assert jan["actual_change"] == pytest.approx(0.5)


def test_prior_month_value_is_latest_vintage_strictly_before_release() -> None:
    rows = [
        _vint("2019-12-01", "2020-01-10", 150000.0),
        _vint("2020-01-01", "2020-02-07", 150200.0),  # Jan first print
        _vint("2020-01-01", "2020-02-26", 150300.0),  # revision BETWEEN releases
        _vint("2020-01-01", "2020-03-06", 150999.0),  # same-day revision: excluded
        _vint("2020-02-01", "2020-03-06", 150500.0),  # Feb first print (release r)
    ]

    changes = first_print_changes(_frame(rows), "diff")

    feb = changes.loc[changes["ref_date"] == pd.Timestamp("2020-02-01")].iloc[0]
    assert feb["prior_value"] == pytest.approx(150300.0)  # the revision, not 150200
    assert feb["actual_change"] == pytest.approx(200.0)
    assert feb["prior_pub"] < feb["pub_date"]


# --- THE no-lookahead test -------------------------------------------------------


def test_expectation_immune_to_prints_published_at_or_after_release() -> None:
    """Perturbing anything first published at/after r must not move the
    expectation or the z denominator at r (only the differenced first print
    itself may respond)."""
    rows, refs, pubs = _make_archive(26, "pct", seed=11)
    base = surprise_time_series(first_print_changes(_frame(rows), "pct"))
    k = 20
    r_k = pubs[k]

    # (a) strictly after r_k perturbed -> row k completely unchanged, z included.
    after = _perturb(rows, r_k, include_cutoff=False)
    got_after = surprise_time_series(first_print_changes(_frame(after), "pct"))
    pd.testing.assert_frame_equal(got_after.iloc[: k + 1], base.iloc[: k + 1])

    # (b) at r_k too (incl. a poison same-day revision of an old month):
    # earlier rows unchanged; at row k only actual/raw/z may move — the
    # expectation and the trailing z scale must not.
    at = _perturb(rows, r_k, include_cutoff=True)
    at.append(_vint(refs[10], r_k, 999999.0))
    got_at = surprise_time_series(first_print_changes(_frame(at), "pct"))
    pd.testing.assert_frame_equal(got_at.iloc[:k], base.iloc[:k])
    assert got_at["expectation"].iloc[k] == pytest.approx(base["expectation"].iloc[k])
    assert got_at["surprise_scale"].iloc[k] == pytest.approx(base["surprise_scale"].iloc[k])
    assert got_at["actual_change"].iloc[k] != pytest.approx(base["actual_change"].iloc[k])


# --- strictly-prior windows + min-history rules ----------------------------------


def test_windows_are_strictly_prior_with_min_history_rules() -> None:
    rows, _, _ = _make_archive(26, "diff", seed=3)

    ts = surprise_time_series(first_print_changes(_frame(rows), "diff"))

    # Row 0 has no prior month inside the fixture -> usable changes start at 1.
    assert pd.isna(ts["actual_change"].iloc[0])
    assert ts["actual_change"].notna().iloc[1:].all()
    # Expectation needs >= 6 changes strictly before r -> first defined at row 7,
    # and it equals the mean of the changes at rows 1..6 (never row 7 itself).
    assert not ts["expectation"].notna().iloc[:7].any()
    assert ts["expectation"].notna().iloc[7:].all()
    assert ts["expectation"].iloc[7] == pytest.approx(ts["actual_change"].iloc[1:7].mean())
    # z needs >= 12 raw surprises strictly before r; raws exist from row 7 ->
    # first z at row 19, scaled by std(raw[7..18], ddof=1).
    assert not ts["surprise_z"].notna().iloc[:19].any()
    assert ts["surprise_z"].notna().iloc[19:].all()
    assert ts["surprise_scale"].iloc[19] == pytest.approx(
        ts["raw_surprise"].iloc[7:19].std(ddof=1)
    )
    assert (ts["surprise_z"].dropna().abs() <= Z_CLIP).all()


# --- event matching + zero-fill + fail-loud guard ---------------------------------


def test_build_surprise_features_end_to_end_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_network(monkeypatch)
    cpi_rows, _, cpi_pubs = _make_archive(30, "pct", seed=1)
    cpi_rows.append(_vint("2019-01-01", "2019-02-13", "."))  # "." parses to NaN, dropped
    nfp_rows, _, nfp_pubs = _make_archive(30, "diff", seed=2, base=150000.0)
    _write_cache(tmp_path, "CPIAUCSL", cpi_rows)
    _write_cache(tmp_path, "PAYEMS", nfp_rows)
    events = _events(
        [
            ("CPI", cpi_pubs[22]),  # exact-date match
            ("CPI", cpi_pubs[23] + pd.Timedelta(days=1)),  # tolerant -1d match
            ("CPI", cpi_pubs[3]),  # matched but insufficient history -> 0/0
            ("NFP", nfp_pubs[24]),  # exact-date match, PAYEMS series
            ("FOMC", pd.Timestamp("2021-06-16")),  # no surprise defined
        ]
    )

    out = build_surprise_features(events, fred_api_key="offline", cache_dir=tmp_path)

    assert out.index.name == "event_id"
    assert list(out.columns) == ["surprise_z", "has_surprise"]
    assert len(out) == 5
    assert out.loc["FOMC_20210616"].tolist() == [0.0, 0.0]
    early_id = f"CPI_{cpi_pubs[3]:%Y%m%d}"
    assert out.loc[early_id].tolist() == [0.0, 0.0]
    matched = out.drop(index=["FOMC_20210616", early_id])
    assert (matched["has_surprise"] == 1.0).all()
    assert (matched["surprise_z"] != 0.0).all()
    assert (matched["surprise_z"].abs() <= Z_CLIP).all()
    # Exact-value cross-check against the unit-level pipeline (cache-hit path).
    vintages = fetch_alfred_vintages("CPIAUCSL", "offline", tmp_path)
    ts = surprise_time_series(first_print_changes(vintages, "pct"))
    expected = float(ts.loc[ts["pub_date"] == cpi_pubs[22], "surprise_z"].iloc[0])
    assert out.loc[f"CPI_{cpi_pubs[22]:%Y%m%d}", "surprise_z"] == pytest.approx(expected)


def test_unmatched_share_over_threshold_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_network(monkeypatch)
    cpi_rows, _, pubs = _make_archive(30, "pct", seed=5)
    _write_cache(tmp_path, "CPIAUCSL", cpi_rows)
    good = [("CPI", pubs[k]) for k in (20, 21, 22, 23)]
    bad = [
        ("CPI", pubs[24] + pd.Timedelta(days=5)),
        ("CPI", pubs[25] + pd.Timedelta(days=5)),
    ]  # 2/6 unmatched = 33% > 20%

    with pytest.raises(RuntimeError, match="matching failed"):
        build_surprise_features(_events(good + bad), fred_api_key="offline", cache_dir=tmp_path)


def test_unmatched_share_under_threshold_zero_fills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_network(monkeypatch)
    cpi_rows, _, pubs = _make_archive(30, "pct", seed=5)
    _write_cache(tmp_path, "CPIAUCSL", cpi_rows)
    good = [("CPI", pubs[k]) for k in (19, 20, 21, 22, 23)]
    bad_day = pubs[24] + pd.Timedelta(days=5)  # 1/6 unmatched ~ 17% <= 20%

    out = build_surprise_features(
        _events(good + [("CPI", bad_day)]), fred_api_key="offline", cache_dir=tmp_path
    )

    assert out.loc[f"CPI_{bad_day:%Y%m%d}"].tolist() == [0.0, 0.0]
    assert out["has_surprise"].sum() == 5.0


def test_fomc_only_events_need_no_data_fetch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_network(monkeypatch)
    events = _events([("FOMC", pd.Timestamp("2024-03-20")), ("FOMC", pd.Timestamp("2024-05-01"))])

    out = build_surprise_features(events, fred_api_key="", cache_dir=tmp_path)

    assert out.index.name == "event_id"
    assert (out["surprise_z"] == 0.0).all()
    assert (out["has_surprise"] == 0.0).all()


def test_no_forward_match_a_future_release_is_lookahead(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An event dated one day BEFORE a release must NOT borrow that release's
    surprise — at event_ts the release is future information (lookahead). Pins
    the backward-only match fix: the day-before event is zero-filled."""
    _no_network(monkeypatch)
    cpi_rows, _, pubs = _make_archive(30, "pct", seed=7)
    _write_cache(tmp_path, "CPIAUCSL", cpi_rows)
    day_before = pubs[22] - pd.Timedelta(days=1)  # exactly 1 day before a real print
    # Indices >= 19 carry a valid z (z needs >= 12 strictly-prior raw surprises,
    # first available at row 19); index 18 would be nan_z and conflate the check.
    matched = [("CPI", pubs[k]) for k in (19, 20, 21, 23, 24)]  # 5 exact-date matches

    out = build_surprise_features(
        _events(matched + [("CPI", day_before)]),
        fred_api_key="offline",
        cache_dir=tmp_path,
    )

    # The day-before event must be zero-filled: no forward match to pubs[22].
    assert out.loc[f"CPI_{day_before:%Y%m%d}"].tolist() == [0.0, 0.0]
    # The 5 exact-date matches still resolve (1/6 unmatched ~ 17% <= 20% guard).
    assert out["has_surprise"].sum() == 5.0


# --- date-broadcast helper (Phase C cross-section feature) -------------------


def test_date_broadcast_is_pit_step_function_nan_before_first_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The broadcast at d = the most recent surprise_z published <= d; NaN before
    the first release with a computable z. Verified by recomputing the expected
    step function from the module's own transforms (offline)."""
    _no_network(monkeypatch)
    rows, _refs, _pubs = _make_archive(n_months=26, kind="pct", seed=0)
    _write_cache(tmp_path, "CPIAUCSL", rows)

    dates = pd.date_range("2018-12-01", "2021-06-01", freq="W-MON").normalize()
    got = macro_surprise_date_broadcast(
        "CPIAUCSL", dates, "offline", tmp_path, name="macro_cpi_surprise"
    )

    # expected: dropna surprise_z, dedup pub_date (headline), backward merge_asof
    vint = fetch_alfred_vintages("CPIAUCSL", "offline", tmp_path)
    ts = surprise_time_series(first_print_changes(vint, "pct"))
    head = (
        ts.dropna(subset=["surprise_z"])
        .sort_values(["pub_date", "ref_date"])
        .drop_duplicates("pub_date", keep="last")[["pub_date", "surprise_z"]]
        .sort_values("pub_date")
    )
    head["pub_date"] = head["pub_date"].dt.normalize()
    exp = pd.merge_asof(
        pd.DataFrame({"date": dates}),
        head.rename(columns={"pub_date": "date"}),
        on="date", direction="backward",
    )["surprise_z"].to_numpy()

    np.testing.assert_array_equal(got.to_numpy(), exp)
    assert got.name == "macro_cpi_surprise"
    assert list(got.index) == list(dates)

    # strictly before the first release with a computable z -> NaN (PIT)
    first_pub = head["pub_date"].iloc[0]
    pre = got.index[got.index < first_pub]
    assert len(pre) > 0
    assert got.loc[pre].isna().all()

    # after the last release the value is constant (carries the last surprise)
    last_pub = head["pub_date"].iloc[-1]
    tail = got.loc[got.index > last_pub]
    assert len(tail) > 0
    assert tail.nunique() == 1
    assert tail.iloc[0] == head["surprise_z"].iloc[-1]


def test_date_broadcast_rejects_unknown_series() -> None:
    import pytest as _pytest

    with _pytest.raises(ValueError, match="no change_kind"):
        macro_surprise_date_broadcast("NOTASERIES", pd.DatetimeIndex([]), "offline")
