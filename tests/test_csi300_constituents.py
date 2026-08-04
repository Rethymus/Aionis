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

    # Assert: should generate daily rows from 2018-01-15 to far future
    assert list(df.columns) == ["date", "ticker"]
    assert df["ticker"].unique()[0] == "SZ000001"
    assert df["date"].min() == pd.Timestamp("2018-01-15")
    assert df["date"].max() == pd.Timestamp("2099-12-31")  # far future
    # Count days from 2018-01-15 to 2099-12-31 inclusive
    expected_days = (pd.Timestamp("2099-12-31") - pd.Timestamp("2018-01-15")).days + 1
    assert len(df) == expected_days


def test_parse_opt_in_opt_out_with_exit_date(_mock_index_constitution):
    # Arrange: stock joined 2018-01-15, exited 2019-06-20
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000002", "name": "万科A", "opt-in": "2018-01-15", "opt-out": "2019-06-20"},
    ])

    # Act
    df = csi300_constituents._parse_opt_in_opt_out_to_long(
        _mock_index_constitution.history_data
    )

    # Assert: daily rows from opt-in to opt_out (exclusive)
    assert df["date"].min() == pd.Timestamp("2018-01-15")
    assert df["date"].max() == pd.Timestamp("2019-06-20")
    # Count days from 2018-01-15 to 2019-06-20 inclusive
    expected_days = (pd.Timestamp("2019-06-20") - pd.Timestamp("2018-01-15")).days + 1
    assert len(df) == expected_days


def test_parse_opt_in_opt_out_single_day_membership(_mock_index_constitution):
    # Arrange: stock joined and exited same day (opt-in == opt-out)
    _mock_index_constitution.history_data = pd.DataFrame([
        {"symbol": "SZ000003", "name": "神州高铁", "opt-in": "2018-06-15", "opt-out": "2018-06-15"},
    ])

    # Act
    df = csi300_constituents._parse_opt_in_opt_out_to_long(
        _mock_index_constitution.history_data
    )

    # Assert: one row for that single day
    assert len(df) == 1
    assert df["date"].iloc[0] == pd.Timestamp("2018-06-15")
    assert df["ticker"].iloc[0] == "SZ000003"


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
    # Check that SZ000002 only appears in 2019
    sz000002_rows = df[df["ticker"] == "SZ000002"]
    assert sz000002_rows["date"].min() == pd.Timestamp("2019-01-01")
    assert sz000002_rows["date"].max() == pd.Timestamp("2019-12-31")


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
