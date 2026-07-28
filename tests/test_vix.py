"""VIX ingest invariants — hermetic (no network).

Pins the PIT discipline of :mod:`aionis.ingest.vix`: the as-of join returns the
value knowable at t (a VIX close released on day d is visible at d but NOT at
d-1), NaN before the first release, revision-safe, deterministic, and cache hits
make no fetch. Mirrors the offline-vintage pattern of ``test_macro_surprise.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import requests

from aionis.ingest import vix

# --- fixture builders (ALFRED-shaped vintage rows, offline) -------------------


def _vint(ref: str, pub: str, value: float) -> dict:
    """One ALFRED observation row (FRED serializes values as strings)."""
    return {
        "date": pd.Timestamp(ref).strftime("%Y-%m-%d"),
        "realtime_start": pd.Timestamp(pub).strftime("%Y-%m-%d"),
        "value": str(value),
    }


def _write_vintages(cache_dir: Path, rows: list[dict]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "alfred_VIXCLS.json").write_text(json.dumps({"observations": rows}))


def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("network call attempted in offline test")

    monkeypatch.setattr(requests, "get", _boom)


# --- vix_as_of PIT invariants -------------------------------------------------


def test_as_of_value_released_on_d_is_visible_at_d_not_d_minus_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_network(monkeypatch)
    rows = [
        _vint("2024-01-02", "2024-01-02", 15.0),
        _vint("2024-01-03", "2024-01-03", 16.0),  # released on the 3rd
    ]
    _write_vintages(tmp_path, rows)
    dates = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-04"]).normalize()

    s = vix.vix_as_of(dates, cache_dir=tmp_path)

    assert s.name == "vix"
    assert s.loc["2024-01-02"] == 15.0
    assert s.loc["2024-01-03"] == 16.0  # visible on its own release day
    assert s.loc["2024-01-04"] == 16.0  # carries forward the latest knowable
    # The value released on the 3rd is NOT visible on the 2nd (PIT):
    assert s.loc["2024-01-02"] != 16.0


def test_as_of_nan_before_first_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_network(monkeypatch)
    rows = [_vint("2024-01-02", "2024-01-02", 15.0)]
    _write_vintages(tmp_path, rows)
    dates = pd.DatetimeIndex(["2023-12-29", "2024-01-01", "2024-01-02"]).normalize()

    s = vix.vix_as_of(dates, cache_dir=tmp_path)

    assert pd.isna(s.loc["2023-12-29"])
    assert pd.isna(s.loc["2024-01-01"])
    assert s.loc["2024-01-02"] == 15.0


def test_as_of_revision_uses_value_knowable_at_the_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A revised VIX value republished later is invisible until its publication
    date — at d you used what was knowable then (the original), then the revision.
    """
    _no_network(monkeypatch)
    rows = [
        _vint("2024-01-02", "2024-01-02", 15.0),
        _vint("2024-01-02", "2024-01-09", 14.8),  # revision published the 9th
    ]
    _write_vintages(tmp_path, rows)
    dates = pd.DatetimeIndex(["2024-01-05", "2024-01-10"]).normalize()

    s = vix.vix_as_of(dates, cache_dir=tmp_path)

    assert s.loc["2024-01-05"] == 15.0  # before the revision was published
    assert s.loc["2024-01-10"] == 14.8  # after the revision was published


def test_as_of_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_network(monkeypatch)
    rows = [
        _vint("2024-01-02", "2024-01-02", 15.0),
        _vint("2024-01-03", "2024-01-03", 16.0),
        _vint("2024-01-04", "2024-01-04", 17.0),
    ]
    _write_vintages(tmp_path, rows)
    dates = pd.DatetimeIndex(pd.date_range("2024-01-02", "2024-01-06"))

    a = vix.vix_as_of(dates, cache_dir=tmp_path)
    b = vix.vix_as_of(dates, cache_dir=tmp_path)

    pd.testing.assert_series_equal(a, b)


# --- fetch_vix cache + ledger -------------------------------------------------


def test_fetch_vix_cache_hit_makes_no_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("pdr fetch attempted on cache hit")

    monkeypatch.setattr("pandas_datareader.get_data_fred", _boom)
    cached = pd.Series(
        [15.0, 16.0], index=pd.to_datetime(["2024-01-02", "2024-01-03"]), name="vix"
    )
    cached.index.name = "date"
    cdir = tmp_path / "cache"
    cdir.mkdir()
    pd.DataFrame({"date": cached.index, "vix": cached.to_numpy()}).to_parquet(
        cdir / "vix_cls.parquet"
    )

    s = vix.fetch_vix("2024-01-02", "2024-01-03", cache_dir=cdir)

    assert s.name == "vix"
    assert s.index.name == "date"
    assert list(s.index) == list(cached.index)
    assert s.tolist() == [15.0, 16.0]


def test_fetch_vix_writes_cache_and_logs_ingest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    synth = pd.DataFrame(
        {"VIXCLS": [15.0, 16.0, 17.0]},
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
    )
    monkeypatch.setattr("pandas_datareader.get_data_fred", lambda *a, **k: synth)
    # redirect ledger writes into the tmp tree (hermetic — real ledger untouched)
    monkeypatch.setattr(vix.settings, "runs_dir", tmp_path)
    cdir = tmp_path / "cache"

    s = vix.fetch_vix("2024-01-02", "2024-01-04", cache_dir=cdir)

    assert s.tolist() == [15.0, 16.0, 17.0]
    assert s.index.name == "date"
    assert (cdir / "vix_cls.parquet").exists()  # cache written

    # second call hits cache -> reader NOT consulted (would boom if it were)
    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("fetch attempted on cache hit")

    monkeypatch.setattr("pandas_datareader.get_data_fred", _boom)
    s2 = vix.fetch_vix("2024-01-02", "2024-01-04", cache_dir=cdir)
    pd.testing.assert_series_equal(s, s2)

    ledger = (tmp_path / "ledger.jsonl").read_text().strip().splitlines()
    assert len(ledger) == 1  # appended once, on the actual fetch only
    row = json.loads(ledger[0])
    assert row["event"] == "data_ingest"
    assert row["dataset"] == "VIXCLS"
    assert row["source"] == "FRED/ALFRED"
    assert row["license"] == "FRED public terms"
    assert row["mode"] == "exploratory"
    assert row["n_rows"] == 3
    assert row["range"] == ["2024-01-02", "2024-01-04"]
    assert "data_sha256" in row and len(row["data_sha256"]) == 64
    assert "as_of" in row


# --- unrevised-series synthesis (VIXCLS has no ALFRED vintages) --------------


def test_vix_as_of_synthesizes_self_dated_vintages_when_no_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """VIXCLS is unrevised and NOT vintage-tracked on ALFRED (the realtime endpoint
    400s). With no cached vintages, ``_download_vix_vintages`` fetches the realized
    series and synthesizes SELF-DATED vintages (``realtime_start == date``);
    ``vix_as_of`` then returns the unrevised series PIT-correctly — value at d is
    VIX[d], NaN before the first observation, carried forward after the last."""
    synth = pd.Series(
        [15.0, 16.0, 17.0],
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
    )
    synth.name = "VIXCLS"
    monkeypatch.setattr("pandas_datareader.get_data_fred", lambda *a, **k: synth.to_frame())
    monkeypatch.setattr(vix.settings, "fred_api_key", "test-key")
    # no alfred_VIXCLS.json present -> forces the synthesized download path
    dates = pd.DatetimeIndex(pd.date_range("2024-01-01", "2024-01-05")).normalize()

    s = vix.vix_as_of(dates, cache_dir=tmp_path)

    assert s.name == "vix"
    assert pd.isna(s.loc["2024-01-01"])          # before the first observation
    assert s.loc["2024-01-02"] == 15.0           # knowable at its own date
    assert s.loc["2024-01-03"] == 16.0
    assert s.loc["2024-01-04"] == 17.0
    assert s.loc["2024-01-05"] == 17.0           # carries the last knowable close
    # the synthesized self-dated vintages were cached
    cache = tmp_path / "alfred_VIXCLS.json"
    assert cache.exists()
    import json as _json

    rows = _json.loads(cache.read_text())["observations"]
    assert all(r["date"] == r["realtime_start"] for r in rows)  # self-dated
    assert len(rows) == 3
