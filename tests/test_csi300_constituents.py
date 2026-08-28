"""Hermetic tests for the CSI300 constituents ingest adapter.

index-constitution is mocked via ``sys.modules`` — no real network, no package import.
Exercises the opt-in/opt-out to long format transform, PIT membership query,
cache hit/miss logic, and lazy import guard.
"""
from __future__ import annotations

import sys
import types

import pandas as pd
import pytest

from aionis.ingest import csi300_constituents

_CSV_COLUMNS = ["symbol", "name", "opt-in", "opt-out"]


class _FakeIndexConstitution:
    """Mimics index_constitution module with ``history()`` returning canned data."""

    def __init__(self, history_data: list[dict[str, str]]) -> None:
        self.history_data = history_df = pd.DataFrame(history_data)
        # Ensure column names match expected format
        assert list(history_df.columns) == _CSV_COLUMNS

    def history(self, index: str) -> pd.DataFrame:
        """Return canned history DataFrame."""
        if index != "csi300":
            raise ValueError(f"Unknown index: {index}")
        return self.history_data


@pytest.fixture
def _mock_index_constitution(monkeypatch):
    """Install a fresh fake index_constitution module; return it for per-test data setup."""

    # Default minimal data: one stock that joined in 2018, still in
    history_data = [
        {"symbol": "SZ000001", "name": "平安银行", "opt-in": "2018-01-15", "opt-out": ""},
    ]
    fake = _FakeIndexConstitution(history_data)
    mod = types.ModuleType("index_constitution")
    mod.history = fake.history  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "index_constitution", mod)
    return fake


def test_lazy_import_guard_without_package_installed():
    # Arrange: index_constitution not in sys.modules
    # Act / Assert: ImportError with helpful message
    with pytest.raises(ImportError, match="index-constitution is required"):
        # Force re-import by clearing cached module if present
        sys.modules.pop("index_constitution", None)
        csi300_constituents._require_index_constitution()


def test_parse_opt_in_opt_out_to_long_expands_daily(_mock_index_constitution):
    # Arrange: stock joined 2018-01-15, still in (opt-out empty)
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000001", "name": "平安银行", "opt-in": "2018-01-15", "opt-out": ""},
    ])

    # Act
    df = csi300_constituents._parse_opt_in_opt_out_to_long(
        _mock_index_constitution.history_data
    )

    # Assert: still-member is capped at the SNAPSHOT date (today), not 2099-12-31.
    # Half-open [opt_in, opt_out): the snapshot cap day itself yields no row.
    today = pd.Timestamp.today().normalize()
    assert list(df.columns) == ["date", "ticker"]
    assert df["ticker"].unique()[0] == "SZ000001"
    assert df["date"].min() == pd.Timestamp("2018-01-15")
    assert df["date"].max() == today - pd.Timedelta(days=1)
    expected_days = (today - pd.Timestamp("2018-01-15")).days
    assert len(df) == expected_days


def test_parse_handles_nat_opt_in_as_data_start(_mock_index_constitution):
    """NaT opt-in (stock predates dataset) -> member from earliest known opt-in."""
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000001", "name": "anchor", "opt-in": "2010-01-04", "opt-out": ""},
        {"symbol": "SH600549", "name": "NaTin", "opt-in": None, "opt-out": "2019-06-17"},
    ])
    df = csi300_constituents._parse_opt_in_opt_out_to_long(_mock_index_constitution.history_data)
    sub = df[df["ticker"] == "SH600549"]
    # NaT opt-in falls back to data_start (2010-01-04); opt-out honored.
    # Half-open [opt_in, opt_out): last member day = opt-out - 1.
    assert sub["date"].min() == pd.Timestamp("2010-01-04")
    assert sub["date"].max() == pd.Timestamp("2019-06-16")


def test_parse_skips_row_with_both_nat(_mock_index_constitution):
    """Both opt-in and opt-out NaT -> row skipped (cannot place membership)."""
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000001", "name": "good", "opt-in": "2018-01-15", "opt-out": "2019-01-15"},
        {"symbol": "SH999999", "name": "unplaceable", "opt-in": None, "opt-out": None},
    ])
    df = csi300_constituents._parse_opt_in_opt_out_to_long(_mock_index_constitution.history_data)
    assert "SH999999" not in set(df["ticker"])
    assert "SZ000001" in set(df["ticker"])


def test_parse_opt_in_opt_out_with_exit_date(_mock_index_constitution):
    # Arrange: stock joined 2018-01-15, exited 2019-06-20
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000002", "name": "万科A", "opt-in": "2018-01-15", "opt-out": "2019-06-20"},
    ])

    # Act
    df = csi300_constituents._parse_opt_in_opt_out_to_long(
        _mock_index_constitution.history_data
    )

    # Assert: daily rows [opt_in, opt_out) — removal day 2019-06-20 EXCLUDED
    assert df["date"].min() == pd.Timestamp("2018-01-15")
    assert df["date"].max() == pd.Timestamp("2019-06-19")
    expected_days = (pd.Timestamp("2019-06-20") - pd.Timestamp("2018-01-15")).days
    assert len(df) == expected_days


def test_parse_half_open_membership_excludes_opt_out_day(_mock_index_constitution):
    """P1-8 regression: the removal day (opt-out) must NOT be a member day.

    Half-open [opt_in, opt_out) semantics: 2020-06-15 (opt-out) absent,
    2020-06-14 (last member day) present.
    """
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000004", "name": "边界", "opt-in": "2020-01-01", "opt-out": "2020-06-15"},
    ])
    df = csi300_constituents._parse_opt_in_opt_out_to_long(
        _mock_index_constitution.history_data
    )
    dates = set(df["date"])
    assert pd.Timestamp("2020-06-15") not in dates  # removal day: not a member
    assert pd.Timestamp("2020-06-14") in dates  # last member day
    assert pd.Timestamp("2020-01-01") in dates  # opt-in day: member (inclusive)
    expected_days = (pd.Timestamp("2020-06-15") - pd.Timestamp("2020-01-01")).days
    assert len(df) == expected_days


def test_parse_one_day_window_yields_single_member_day(_mock_index_constitution):
    """Boundary: opt_out == opt_in + 1 -> exactly one member day (the opt-in day)."""
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000005", "name": "单日", "opt-in": "2020-01-01", "opt-out": "2020-01-02"},
    ])
    df = csi300_constituents._parse_opt_in_opt_out_to_long(
        _mock_index_constitution.history_data
    )
    assert len(df) == 1
    assert df["date"].iloc[0] == pd.Timestamp("2020-01-01")
    assert df["ticker"].iloc[0] == "SZ000005"


def test_constituents_on_removal_day_not_member(_mock_index_constitution, tmp_path):
    """PIT query ON the opt-out day must not see the removed stock (half-open)."""
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000004", "name": "边界", "opt-in": "2020-01-01", "opt-out": "2020-06-15"},
    ])
    df = csi300_constituents.fetch_csi300_constituents(
        cache_dir=tmp_path, enable_fetch=True
    )
    assert "SZ000004" not in csi300_constituents.constituents_on(df, "2020-06-15")
    assert "SZ000004" in csi300_constituents.constituents_on(df, "2020-06-14")


def test_parse_opt_in_opt_out_single_day_membership(_mock_index_constitution):
    # Arrange: degenerate interval opt-in == opt-out -> EMPTY membership period
    # (half-open [d, d) contains no days; the stock was never a member row).
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000003", "name": "神州高铁", "opt-in": "2018-06-15", "opt-out": "2018-06-15"},
    ])

    # Act
    df = csi300_constituents._parse_opt_in_opt_out_to_long(
        _mock_index_constitution.history_data
    )

    # Assert: zero membership rows for the degenerate interval
    assert len(df) == 0
    assert list(df.columns) == ["date", "ticker"]


def test_parse_opt_in_opt_out_multiple_stocks(_mock_index_constitution):
    # Arrange: two stocks with different membership periods
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000001", "name": "平安银行", "opt-in": "2018-01-15", "opt-out": ""},
        {"symbol": "SZ000002", "name": "万科A", "opt-in": "2019-01-01", "opt-out": "2019-12-31"},
    ])

    # Act
    df = csi300_constituents._parse_opt_in_opt_out_to_long(
        _mock_index_constitution.history_data
    )

    # Assert: both stocks present
    assert set(df["ticker"].unique()) == {"SZ000001", "SZ000002"}
    # Check that SZ000002 only appears in 2019 (half-open: [2019-01-01, 2019-12-31))
    sz000002_rows = df[df["ticker"] == "SZ000002"]
    assert sz000002_rows["date"].min() == pd.Timestamp("2019-01-01")
    assert sz000002_rows["date"].max() == pd.Timestamp("2019-12-30")


def test_fetch_csi300_constituents_enable_fetch_true(_mock_index_constitution, tmp_path):
    # Arrange: enable_fetch=True should read from mocked module
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000001", "name": "平安银行", "opt-in": "2018-01-15", "opt-out": "2019-12-31"},
    ])

    # Act
    df = csi300_constituents.fetch_csi300_constituents(
        cache_dir=tmp_path, enable_fetch=True
    )

    # Assert: should return parsed long format
    assert set(df.columns) == {"date", "ticker"}
    assert len(df) > 0
    assert "SZ000001" in df["ticker"].values

    # Check cache file created
    assert (tmp_path / "csi300_constituents.parquet").exists()


def test_fetch_csi300_constituents_cache_hit(_mock_index_constitution, tmp_path):
    # Arrange: create cached parquet first
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000001", "name": "平安银行", "opt-in": "2018-01-15", "opt-out": ""},
    ])
    csi300_constituents.fetch_csi300_constituents(
        cache_dir=tmp_path, enable_fetch=True
    )

    # Act: second call should hit cache (enable_fetch irrelevant)
    df2 = csi300_constituents.fetch_csi300_constituents(
        cache_dir=tmp_path, enable_fetch=False
    )

    # Assert: cache hit returns same data
    assert len(df2) > 0
    assert "SZ000001" in df2["ticker"].values


def test_fetch_csi300_constituents_cache_miss_fetch_disabled(_mock_index_constitution, tmp_path):
    # Arrange: no cache exists, enable_fetch=False
    # Act / Assert: should raise FileNotFoundError
    with pytest.raises(FileNotFoundError, match="Cached CSI300 constituents not found"):
        csi300_constituents.fetch_csi300_constituents(
            cache_dir=tmp_path, enable_fetch=False
        )


def test_constituents_on_pit_query(_mock_index_constitution, tmp_path):
    # Arrange: stock joined 2018-01-15, exited 2019-12-31
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000001", "name": "平安银行", "opt-in": "2018-01-15", "opt-out": "2019-12-31"},
    ])
    df = csi300_constituents.fetch_csi300_constituents(
        cache_dir=tmp_path, enable_fetch=True
    )

    # Act: query membership during active period
    members_2018 = csi300_constituents.constituents_on(df, "2018-06-30")

    # Assert: stock should be present
    assert "SZ000001" in members_2018

    # Act: query membership after exit
    members_2020 = csi300_constituents.constituents_on(df, "2020-06-30")

    # Assert: stock should NOT be present (no forward-fill)
    assert "SZ000001" not in members_2020


def test_constituents_on_before_entry(_mock_index_constitution, tmp_path):
    # Arrange: stock joined 2018-01-15
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000001", "name": "平安银行", "opt-in": "2018-01-15", "opt-out": ""},
    ])
    df = csi300_constituents.fetch_csi300_constituents(
        cache_dir=tmp_path, enable_fetch=True
    )

    # Act: query membership before entry (2017-12-31)
    members_2017 = csi300_constituents.constituents_on(df, "2017-12-31")

    # Assert: stock should NOT be present (no look-ahead)
    assert "SZ000001" not in members_2017


def test_verify_snapshot_integrity_pass(_mock_index_constitution, tmp_path):
    # Arrange: create valid snapshot
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000001", "name": "平安银行", "opt-in": "2018-01-15", "opt-out": ""},
    ])
    df = csi300_constituents.fetch_csi300_constituents(
        cache_dir=tmp_path, enable_fetch=True
    )

    # Act / Assert: should pass with expected range
    assert csi300_constituents.verify_snapshot_integrity(
        df,
        expected_date_range=("2018-01-01", "2099-12-31"),
        expected_n_constituents=1,
    )


def test_verify_snapshot_integrity_empty_dataframe():
    # Arrange: empty DataFrame
    df = pd.DataFrame(columns=["date", "ticker"])

    # Act / Assert: should raise ValueError
    with pytest.raises(ValueError, match="DataFrame is empty"):
        csi300_constituents.verify_snapshot_integrity(
            df, expected_date_range=("2018-01-01", "2099-12-31")
        )


def test_verify_snapshot_integrity_date_mismatch(_mock_index_constitution, tmp_path):
    # Arrange: create snapshot with wrong date range
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000001", "name": "平安银行", "opt-in": "2018-01-15", "opt-out": ""},
    ])
    df = csi300_constituents.fetch_csi300_constituents(
        cache_dir=tmp_path, enable_fetch=True
    )

    # Act / Assert: should fail with wrong expected start date
    with pytest.raises(ValueError, match="Date range start mismatch"):
        csi300_constituents.verify_snapshot_integrity(
            df, expected_date_range=("2019-01-01", "2099-12-31")  # starts after actual
        )


def test_verify_snapshot_integrity_constituent_count_mismatch(_mock_index_constitution, tmp_path):
    # Arrange: create snapshot with 1 constituent
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000001", "name": "平安银行", "opt-in": "2018-01-15", "opt-out": ""},
    ])
    df = csi300_constituents.fetch_csi300_constituents(
        cache_dir=tmp_path, enable_fetch=True
    )

    # Act / Assert: should fail with wrong expected count
    with pytest.raises(ValueError, match="Unique ticker count mismatch"):
        csi300_constituents.verify_snapshot_integrity(
            df,
            expected_date_range=("2018-01-01", "2099-12-31"),
            expected_n_constituents=999,  # wrong count
        )
