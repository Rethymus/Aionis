"""Tests for macro_headline.py — anti-degeneracy suite (catch slop).

Tests enforce:
- Surprise values are finite (not all NaN/0/Inf)
- No future leakage: mutating a future value doesn't affect past as-of values
- Term/credit spreads vary cross-sectionally (not CONSTANT)
- Vintage cache is idempotent (second call hits cache, no re-download)
- As-of merge is strictly before (allow_exact_matches=False enforced)

Hermetic ALFRED fixtures: the fetchers short-circuit on the on-disk cache file
(``alfred_{series_id}.json``) BEFORE any HTTP call, so pre-writing realistic
payloads into a tmp cache dir exercises the exact public-function path with
zero network. No pytest.skip anywhere (repo DoD forbids placeholder skips).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from pandas.api.types import is_datetime64_any_dtype

from aionis.features.macro_headline import (
    DAILY_SURPRISE_MIN,
    DAILY_Z_CLIP,
    _daily_asof_series,
    _daily_zscore_series,
    _fetch_with_polite_spacing,
    _first_prints_asof,
    credit_spread,
    dff_surprise,
    fetch_us_macro_4,
    term_spread_1y_10y,
    vix_surprise,
)

# ---------------------------------------------------------------------------
# Hermetic ALFRED cache fixtures (exact on-disk payload shape, no network)
# ---------------------------------------------------------------------------

# 突变截止点：realtime_start >= 该日的观测在"扰动"运行中被改写为 999.0。
# 过去 as-of 日期（< cutoff）只能看到 realtime_start < d < cutoff 的首印，
# 因此两次运行的过去值必须逐点相同。
_CUTOFF = pd.Timestamp("2020-06-01")
_AS_OF_DATES = pd.bdate_range("2020-02-03", "2020-05-29")
_REF_DATES = pd.bdate_range("2019-11-01", "2020-06-30")


def _synthetic_observations(
    ref_dates: pd.DatetimeIndex,
    *,
    base: float,
    step: float,
    corrupt_from: pd.Timestamp | None = None,
) -> list[dict]:
    """Deterministic ALFRED-style observations (first print at ref+1d, revision at ref+3d).

    ``corrupt_from``：realtime_start >= 该日的观测值改写为 999.0（模拟未来
    数据被篡改/修订），用于 no-future-leakage 断言。
    """
    obs: list[dict] = []
    for i, ref in enumerate(ref_dates):
        level = base + step * i
        first_rt = ref + pd.Timedelta(days=1)
        rev_rt = ref + pd.Timedelta(days=3)
        for rt in (first_rt, rev_rt):
            value = 999.0 if (corrupt_from is not None and rt >= corrupt_from) else level
            obs.append({
                "date": ref.strftime("%Y-%m-%d"),
                "realtime_start": rt.strftime("%Y-%m-%d"),
                "value": f"{value:.4f}",
            })
    return obs


def _write_alfred_cache(cache_dir: Path, series_id: str, obs: list[dict]) -> Path:
    """Pre-write the on-disk ALFRED cache file (fetch then short-circuits, no HTTP)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"alfred_{series_id}.json"
    path.write_text(json.dumps({"observations": obs}), encoding="utf-8")
    return path


def _write_series_caches(
    cache_dir: Path,
    series: dict[str, tuple[float, float]],
    *,
    corrupt_from: pd.Timestamp | None = None,
) -> Path:
    """Write one ALFRED cache per series_id: {sid: (base, step)}."""
    for sid, (base, step) in series.items():
        _write_alfred_cache(
            cache_dir, sid, _synthetic_observations(_REF_DATES, base=base, step=step,
                                                    corrupt_from=corrupt_from)
        )
    return cache_dir


def _disable_polite_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """无网络的 hermetic 路径中跳过 ≥2s 礼貌等待（缓存命中本就无 HTTP 调用）。"""
    monkeypatch.setattr(time, "sleep", lambda _s: None)


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Test cache directory (isolated from production cache)."""
    return tmp_path / "cache"


@pytest.fixture
def mock_fred_api_key() -> str:
    """Mock FRED API key (do NOT touch real .env)."""
    return "test_fred_api_key_for_macro_headline"


@pytest.fixture
def mock_vintages_frame() -> pd.DataFrame:
    """Minimal mock ALFRED vintages frame for testing as-of logic."""
    # Create a small realistic vintage pattern:
    # - ref_date: 5 days (2020-01-02 to 2020-01-08)
    # - realtime_start: publication lags by 1 day (FRED daily release pattern)
    # - value: constant 100.0 (simplifies leakage test)
    dates = pd.date_range("2020-01-02", "2020-01-08", freq="B")
    recs = []
    for i, ref_date in enumerate(dates):
        # First print at ref_date + 1 day (publication lag)
        # Revision at ref_date + 3 days (should NOT affect as-of at ref_date+2)
        recs.append({
            "ref_date": ref_date,
            "realtime_start": ref_date + pd.Timedelta(days=1),
            "value": 100.0 + i,  # slight upward trend
        })
        recs.append({
            "ref_date": ref_date,
            "realtime_start": ref_date + pd.Timedelta(days=3),
            "value": 105.0 + i,  # revision (higher)
        })
    return pd.DataFrame(recs)


class TestDailyZscoreSeries:
    """Tests for _daily_zscore_series (the core surprise transform)."""

    def test_zscore_finite_when_sufficient_history(self) -> None:
        """Z-score should be finite (not NaN/Inf) when sufficient history."""
        # Create a series with >DAILY_SURPRISE_MIN values
        # Use values with some variation but not strong trend (more realistic than 1..99)
        import random
        random.seed(42)
        values = [100 + random.uniform(-5, 5) for _ in range(100)]
        series = pd.Series(
            values,
            index=pd.date_range("2020-01-01", periods=100, freq="D"),
            name="test",
        )
        z = _daily_zscore_series(series)

        # shift(1) adds 1 NaN at start, rolling needs DAILY_SURPRISE_MIN values
        # Position 0: NaN (shift), positions 1-20: NaN (insufficient for min_periods=21)
        # Total NaN = DAILY_SURPRISE_MIN
        expected_nan = DAILY_SURPRISE_MIN
        assert z.isna().sum() == expected_nan, f"Expected {expected_nan} NaN, got {z.isna().sum()}"
        # Rest are finite (not Inf)
        finite_z = z.dropna()
        assert (finite_z.abs() < float("inf")).all()
        # Z-score is centered around 0 (roughly)
        assert abs(finite_z.mean()) < 1.0, f"Z-score mean {finite_z.mean():.2f} not near 0"

    def test_zscore_clipped(self) -> None:
        """Z-score should be clipped to ±DAILY_Z_CLIP."""
        # Create a series with extreme jump
        values = [100.0] * 50 + [1000.0]  # 10x jump
        series = pd.Series(
            values,
            index=pd.date_range("2020-01-01", periods=51, freq="D"),
            name="test",
        )
        z = _daily_zscore_series(series)

        # The extreme jump should be clipped
        assert z.dropna().max() <= DAILY_Z_CLIP
        assert z.dropna().min() >= -DAILY_Z_CLIP


class TestFirstPrintsAsOf:
    """Tests for _first_prints_asof (extract minimum realtime_start per ref_date)."""

    def test_extracts_minimum_realtime_start(self, mock_vintages_frame: pd.DataFrame) -> None:
        """Should select the earliest realtime_start per ref_date."""
        fp = _first_prints_asof(mock_vintages_frame)

        # Should have one row per ref_date
        assert len(fp) == mock_vintages_frame["ref_date"].nunique()

        # All realtime_start should be the earliest (first print)
        for ref_date in mock_vintages_frame["ref_date"].unique():
            sub = mock_vintages_frame[mock_vintages_frame["ref_date"] == ref_date]
            min_rt = sub["realtime_start"].min()
            fp_rt = fp.loc[fp["realtime_start"] == min_rt, "realtime_start"]
            assert len(fp_rt) == 1  # exactly one row per ref_date


class TestDailyAsOfSeries:
    """Tests for _daily_asof_series (PIT as-of merge)."""

    def test_asof_returns_datetime_index(self, mock_vintages_frame: pd.DataFrame) -> None:
        """Output should have datetime index."""
        as_of_dates = pd.date_range("2020-01-01", "2020-01-10", freq="B")
        result = _daily_asof_series(as_of_dates, mock_vintages_frame, "test")

        assert isinstance(result.index, pd.DatetimeIndex)
        assert is_datetime64_any_dtype(result.index)

    def test_asof_strictly_before(self, mock_vintages_frame: pd.DataFrame) -> None:
        """As-of at d should only use data with realtime_start < d."""
        # Target dates: include dates before, at, and after publication
        as_of_dates = pd.DatetimeIndex([
            pd.Timestamp("2020-01-01"),  # before any publication
            pd.Timestamp("2020-01-02"),  # before publication
            pd.Timestamp("2020-01-03"),  # exactly at first publication (2020-01-02 + 1 day)
            pd.Timestamp("2020-01-06"),  # after publication (should have value)
            pd.Timestamp("2020-01-07"),  # after publication (should have value)
        ])
        result = _daily_asof_series(as_of_dates, mock_vintages_frame, "test")

        # First publication is at 2020-01-02 + 1 day = 2020-01-03
        # So as-of at 2020-01-03 should still be NaN (strictly before)
        assert pd.isna(result.loc[pd.Timestamp("2020-01-03")])
        # As-of at 2020-01-06 (after publication) should have value
        assert pd.notna(result.loc[pd.Timestamp("2020-01-06")])


class TestNoFutureLeakage:
    """Tests for future leakage — mutating future values must NOT affect past as-of.

    Hermetic：预写 tmp ALFRED 缓存（命中即零 HTTP），"扰动"运行把
    realtime_start >= _CUTOFF 的观测改写为 999.0；<_CUTOFF 的过去 as-of 值
    在两次运行间必须逐点相同（含 NaN 位置）。
    """

    def test_term_spread_no_future_leakage(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mutating future GS10/TB3MS values should NOT change past term_spread."""
        _disable_polite_sleep(monkeypatch)
        dir_a = _write_series_caches(
            tmp_path / "a", {"GS10": (100.0, 0.5), "TB3MS": (4.0, 0.2)}
        )
        dir_b = _write_series_caches(
            tmp_path / "b", {"GS10": (100.0, 0.5), "TB3MS": (4.0, 0.2)},
            corrupt_from=_CUTOFF,
        )

        past = _AS_OF_DATES[_AS_OF_DATES < _CUTOFF]
        s_a = term_spread_1y_10y(_AS_OF_DATES, "test_key", dir_a)
        s_b = term_spread_1y_10y(_AS_OF_DATES, "test_key", dir_b)

        # 过去值逐点相同（断言非空洞：两次运行过去区间都有有限值）
        pd.testing.assert_series_equal(s_a.loc[past], s_b.loc[past])
        valid = s_a.loc[past].dropna()
        assert len(valid) > 0
        assert (valid.abs() < float("inf")).all()

    def test_credit_spread_no_future_leakage(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mutating future BAA10Y/GS10 values should NOT change past credit_spread."""
        _disable_polite_sleep(monkeypatch)
        dir_a = _write_series_caches(
            tmp_path / "a", {"GS10": (100.0, 0.5), "BAA10Y": (6.0, 0.4)}
        )
        dir_b = _write_series_caches(
            tmp_path / "b", {"GS10": (100.0, 0.5), "BAA10Y": (6.0, 0.4)},
            corrupt_from=_CUTOFF,
        )

        past = _AS_OF_DATES[_AS_OF_DATES < _CUTOFF]
        s_a = credit_spread(_AS_OF_DATES, "test_key", dir_a)
        s_b = credit_spread(_AS_OF_DATES, "test_key", dir_b)

        pd.testing.assert_series_equal(s_a.loc[past], s_b.loc[past])
        valid = s_a.loc[past].dropna()
        assert len(valid) > 0
        assert (valid.abs() < float("inf")).all()

    def test_vix_surprise_no_future_leakage(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mutating future VIXCLS values should NOT change past vix_surprise."""
        _disable_polite_sleep(monkeypatch)
        dir_a = _write_series_caches(tmp_path / "a", {"VIXCLS": (20.0, 0.3)})
        dir_b = _write_series_caches(
            tmp_path / "b", {"VIXCLS": (20.0, 0.3)}, corrupt_from=_CUTOFF
        )

        past = _AS_OF_DATES[_AS_OF_DATES < _CUTOFF]
        s_a = vix_surprise(_AS_OF_DATES, dir_a)
        s_b = vix_surprise(_AS_OF_DATES, dir_b)

        pd.testing.assert_series_equal(s_a.loc[past], s_b.loc[past])
        valid = s_a.loc[past].dropna()
        assert len(valid) > 0
        assert (valid.abs() < float("inf")).all()

    def test_dff_surprise_no_future_leakage(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mutating future DFF values should NOT change past dff_surprise."""
        _disable_polite_sleep(monkeypatch)
        dir_a = _write_series_caches(tmp_path / "a", {"DFF": (2.0, 0.05)})
        dir_b = _write_series_caches(
            tmp_path / "b", {"DFF": (2.0, 0.05)}, corrupt_from=_CUTOFF
        )

        past = _AS_OF_DATES[_AS_OF_DATES < _CUTOFF]
        s_a = dff_surprise(_AS_OF_DATES, dir_a)
        s_b = dff_surprise(_AS_OF_DATES, dir_b)

        pd.testing.assert_series_equal(s_a.loc[past], s_b.loc[past])
        valid = s_a.loc[past].dropna()
        assert len(valid) > 0
        assert (valid.abs() < float("inf")).all()


class TestTermSpreadCreditSpreadVary:
    """Tests for cross-sectional variation (RD-13: not CONSTANT) — hermetic."""

    def test_term_spread_varies_with_synthetic_vintages(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """term_spread should vary across dates (not all same value)."""
        _disable_polite_sleep(monkeypatch)
        cache = _write_series_caches(
            tmp_path / "cache", {"GS10": (100.0, 0.5), "TB3MS": (4.0, 0.2)}
        )
        result = term_spread_1y_10y(_AS_OF_DATES, "test_key", cache)

        valid = result.dropna()
        assert len(valid) > 0, "term_spread has NO valid values"
        assert valid.std() > 0, "term_spread is CONSTANT across dates (std=0)"
        assert (valid.abs() < float("inf")).all()

    def test_credit_spread_varies_with_synthetic_vintages(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """credit_spread should vary across dates (not all same value)."""
        _disable_polite_sleep(monkeypatch)
        cache = _write_series_caches(
            tmp_path / "cache", {"GS10": (100.0, 0.5), "BAA10Y": (6.0, 0.4)}
        )
        result = credit_spread(_AS_OF_DATES, "test_key", cache)

        valid = result.dropna()
        assert len(valid) > 0, "credit_spread has NO valid values"
        assert valid.std() > 0, "credit_spread is CONSTANT across dates (std=0)"
        assert (valid.abs() < float("inf")).all()


class TestVintageCacheIdempotent:
    """Tests for cache idempotence (second call hits cache)."""

    def test_fetch_with_polite_spacing_cache_hit(self, cache_dir: Path) -> None:
        """Second fetch should hit cache (no re-download)."""
        # Mock the download function to count calls
        call_count = 0

        def mock_download(series_id: str, fred_api_key: str) -> dict:
            nonlocal call_count
            call_count += 1
            # Return minimal valid ALFRED payload
            return {
                "observations": [
                    {"date": "2020-01-01", "realtime_start": "2020-01-02", "value": "100.0"}
                ]
            }

        # Patch the internal download function
        with patch("aionis.features.macro_surprise._download_vintages", side_effect=mock_download):
            # First call: cache miss → download
            last_call = [0.0]
            _fetch_with_polite_spacing("TEST", "key", cache_dir, last_call)
            assert call_count == 1, "First call should download"

            # Second call: cache hit → no download
            _fetch_with_polite_spacing("TEST", "key", cache_dir, last_call)
            assert call_count == 1, "Second call should hit cache (no new download)"


class TestAsOfIsStrictlyBefore:
    """Tests that as-of merge enforces allow_exact_matches=False."""

    def test_asof_strictly_before_enforced(self, mock_vintages_frame: pd.DataFrame) -> None:
        """As-of at publication day should NOT include that day's value."""
        as_of_dates = pd.DatetimeIndex([
            # Day 1: before any publication
            pd.Timestamp("2020-01-01"),
            # Day 2: exactly at first publication (2020-01-02 + 1 day = 2020-01-03)
            pd.Timestamp("2020-01-03"),
            # Day 3: after publication
            pd.Timestamp("2020-01-06"),
        ])
        result = _daily_asof_series(as_of_dates, mock_vintages_frame, "test")

        # At exactly the publication day, should be NaN (strictly before)
        assert pd.isna(result.loc[pd.Timestamp("2020-01-03")])

        # After publication, should have value
        assert pd.notna(result.loc[pd.Timestamp("2020-01-06")])


class TestUsMacroSurpriseFinite:
    """Tests that surprise values are finite (not all NaN/0/Inf) — hermetic."""

    def test_fetch_us_macro_4_finite(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """All 4 features should have finite values (not all NaN/Inf)."""
        _disable_polite_sleep(monkeypatch)
        cache = _write_series_caches(
            tmp_path / "cache",
            {
                "GS10": (100.0, 0.5),
                "TB3MS": (4.0, 0.2),
                "BAA10Y": (6.0, 0.4),
                "VIXCLS": (20.0, 0.3),
                "DFF": (2.0, 0.05),
            },
        )
        df = fetch_us_macro_4(_AS_OF_DATES, "test_key", cache)

        assert len(df.columns) == 4
        for col in df.columns:
            valid_count = df[col].notna().sum()
            assert valid_count > 0, f"{col} has NO valid values (all NaN)"
            finite = df[col].dropna()
            assert (finite.abs() < float("inf")).all(), f"{col} has Inf values"


class TestVixDffSurpriseFinite:
    """vix_surprise / dff_surprise end-to-end on synthetic cached vintages (hermetic)."""

    def test_vix_surprise_finite_with_synthetic_cache(
        self, tmp_path: Path
    ) -> None:
        """VIXCLS cache present (tmp) → vix_surprise produces finite values."""
        cache = _write_series_caches(tmp_path / "cache", {"VIXCLS": (20.0, 0.3)})

        result = vix_surprise(_AS_OF_DATES, cache)
        valid = result.dropna()
        assert len(valid) > 0, "vix_surprise has NO valid values"
        assert (valid.abs() < float("inf")).all(), "vix_surprise has Inf values"

    def test_dff_surprise_finite_with_synthetic_cache(
        self, tmp_path: Path
    ) -> None:
        """DFF cache present (tmp) → dff_surprise produces finite values."""
        cache = _write_series_caches(tmp_path / "cache", {"DFF": (2.0, 0.05)})

        result = dff_surprise(_AS_OF_DATES, cache)
        valid = result.dropna()
        assert len(valid) > 0, "dff_surprise has NO valid values"
        assert (valid.abs() < float("inf")).all(), "dff_surprise has Inf values"


class TestPolitenessEnforced:
    """Tests that ≥2s politeness is enforced between FRED calls."""

    def test_polite_sleep_between_calls(self, cache_dir: Path, mock_fred_api_key: str) -> None:
        """Should sleep ≥2s between consecutive FRED API calls."""
        import time

        # Mock download to return minimal valid data
        def mock_download(sid: str, key: str) -> dict:
            return {
                "observations": [
                    {"date": "2020-01-01", "realtime_start": "2020-01-02", "value": "100.0"}
                ]
            }

        with patch("aionis.features.macro_surprise._download_vintages", side_effect=mock_download):
            last_call = [0.0]
            start = time.monotonic()
            _fetch_with_polite_spacing("TEST1", mock_fred_api_key, cache_dir, last_call)
            _fetch_with_polite_spacing("TEST2", mock_fred_api_key, cache_dir, last_call)
            elapsed = time.monotonic() - start

            # Should take at least 2 seconds due to politeness sleep
            assert elapsed >= 2.0, f"Politeness not enforced: {elapsed:.1f}s < 2.0s"
