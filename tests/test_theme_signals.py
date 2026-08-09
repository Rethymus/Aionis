"""Tests for theme_signals module — hermetic, deterministic, AAA pattern."""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

# Import the module to test
from aionis.eval.theme_signals import (
    SIGNAL_POLARITY,
    summarize_theme,
    theme_summary_to_jsonable,
)

# Deterministic random seed
rng = np.random.default_rng(0)


def make_panel(
    n_tickers: int = 50,
    signals: dict[str, list[float]] | None = None,
    include_name: bool = True,
    include_sector: bool = True,
) -> dict:
    """Helper to build a synthetic panel for testing.

    Args:
        n_tickers: Number of tickers in the panel.
        signals: Dict of {signal_name: [values]}. If None, generates default signals.
        include_name: Whether to include a 'name' column.
        include_sector: Whether to include a 'sector' column.

    Returns:
        DataFrame-like dict with columns: ticker, (name), (sector), (signal columns).
    """
    data = {"ticker": [f"T{i:03d}" for i in range(n_tickers)]}

    if include_name:
        data["name"] = [f"Test Company {i}" for i in range(n_tickers)]

    if include_sector:
        sectors = ["Tech", "Healthcare", "Finance", "Energy", "Consumer"]
        data["sector"] = [sectors[i % len(sectors)] for i in range(n_tickers)]

    if signals is None:
        # Default signals: mix of bullish and bearish
        signals = {
            "momentum_21d": (rng.standard_normal(n_tickers) + 1).tolist(),  # Mostly positive
            "volatility_21d": (rng.standard_normal(n_tickers) + 0.5).tolist(),  # Some positive
            "beta_252d": rng.standard_normal(n_tickers).tolist(),
        }

    for sig_name, values in signals.items():
        data[sig_name] = values

    return data


class TestMomentumBullishHigh:
    """Test momentum signal (bullish_high) with uniformly positive values."""

    def test_momentum_uniformly_positive_yields_bullish(self) -> None:
        """(a) momentum panel uniformly positive → direction='bullish', favored=highest momentum."""
        # Arrange: Build panel with uniformly positive momentum
        n = 20
        data = make_panel(
            n_tickers=n,
            signals={"momentum_21d": [0.1 + i * 0.05 for i in range(n)]},
        )

        # Act: Summarize the theme
        import pandas as pd

        panel = pd.DataFrame(data)
        summaries = summarize_theme(panel, ["momentum_21d"], top_n=3)

        # Assert: Direction is bullish, top 3 favored tickers are highest momentum
        assert "momentum_21d" in summaries
        summary = summaries["momentum_21d"]
        assert summary.direction == "bullish"
        assert summary.polarity == "bullish_high"
        assert len(summary.favored) == 3
        assert summary.favored[0]["ticker"] == "T019"  # Highest momentum
        assert summary.favored[0]["value"] == pytest.approx(1.05, rel=0.01)
        assert summary.favored[2]["ticker"] == "T017"  # 3rd highest
        assert summary.n == n

    def test_momentum_mostly_positive_includes_name_and_sector(self) -> None:
        """(f) name/sectors present → included in favored entries."""
        # Arrange: Panel with name and sector columns
        n = 15
        data = make_panel(
            n_tickers=n,
            signals={"momentum_21d": [0.5 + i * 0.1 for i in range(n)]},
            include_name=True,
            include_sector=True,
        )

        # Act
        import pandas as pd

        panel = pd.DataFrame(data)
        summaries = summarize_theme(panel, ["momentum_21d"], top_n=2)

        # Assert: name and sector are in favored entries
        summary = summaries["momentum_21d"]
        assert "name" in summary.favored[0]
        assert "sector" in summary.favored[0]
        assert summary.favored[0]["name"] == "Test Company 14"
        assert summary.favored[0]["sector"] == "Consumer"  # 14 % 5 = 4 (Consumer)


class TestVolatilityBearishHigh:
    """Test volatility signal (bearish_high) with high values."""

    def test_volatility_high_yields_bearish(self) -> None:
        """(b) high volatility panel → direction='bearish', favored=most exposed (highest vol)."""
        # Arrange: Panel with uniformly high volatility
        n = 25
        data = make_panel(
            n_tickers=n,
            signals={"volatility_21d": [0.3 + i * 0.02 for i in range(n)]},
        )

        # Act
        import pandas as pd

        panel = pd.DataFrame(data)
        summaries = summarize_theme(panel, ["volatility_21d"], top_n=5)

        # Assert: Direction is bearish, favored = highest volatility (most exposed)
        assert "volatility_21d" in summaries
        summary = summaries["volatility_21d"]
        assert summary.direction == "bearish"  # High vol is bearish
        assert summary.polarity == "bearish_high"
        assert len(summary.favored) == 5
        # Favored are highest volatility (most exposed to bearish signal)
        assert summary.favored[0]["ticker"] == "T024"  # Highest vol
        assert summary.favored[0]["value"] == pytest.approx(0.78, rel=0.01)

    def test_volatility_low_yields_bullish(self) -> None:
        """Low volatility panel → direction='bullish' (mean < median for bearish_high)."""
        # Arrange: Panel with uniformly low volatility
        n = 20
        data = make_panel(
            n_tickers=n,
            signals={"volatility_21d": [0.1 - i * 0.003 for i in range(n)]},
        )

        # Act
        import pandas as pd

        panel = pd.DataFrame(data)
        summaries = summarize_theme(panel, ["volatility_21d"], top_n=3)

        # Assert: Direction is bullish (low vol is bullish)
        summary = summaries["volatility_21d"]
        assert summary.direction == "bullish"


class TestStrengthRange:
    """Test strength normalization and clipping."""

    def test_strength_in_reasonable_range(self) -> None:
        """(c) strength ∈ reasonable range (clipped to [0, ~3])."""
        # Arrange: Normal distribution
        n = 100
        data = make_panel(
            n_tickers=n,
            signals={"momentum_21d": rng.standard_normal(n).tolist()},
        )

        # Act
        import pandas as pd

        panel = pd.DataFrame(data)
        summaries = summarize_theme(panel, ["momentum_21d"])

        # Assert: Strength is non-negative and bounded
        summary = summaries["momentum_21d"]
        assert summary.strength >= 0.0
        assert summary.strength <= 3.0  # Clipped

    def test_strength_clipping_extreme_values(self) -> None:
        """Extreme z-scores → strength clipped to ~3."""
        # Arrange: Very spread out values (extreme z-scores)
        n = 50
        data = make_panel(
            n_tickers=n,
            signals={"momentum_21d": [i * 10 for i in range(n)]},
        )

        # Act
        import pandas as pd

        panel = pd.DataFrame(data)
        summaries = summarize_theme(panel, ["momentum_21d"])

        # Assert: Strength is clipped to ~3
        summary = summaries["momentum_21d"]
        assert summary.strength <= 3.1  # Allow small epsilon


class TestInsufficientData:
    """Test handling of signals with insufficient data."""

    def test_less_than_10_finite_values_skipped(self) -> None:
        """(d) <10 finite values → signal skipped (not in output)."""
        # Arrange: Panel with only 5 finite values
        data = make_panel(n_tickers=5, signals={"momentum_21d": [0.1, 0.2, 0.3, 0.4, 0.5]})

        # Act
        import pandas as pd

        panel = pd.DataFrame(data)
        summaries = summarize_theme(panel, ["momentum_21d"])

        # Assert: Signal not present in summaries
        assert "momentum_21d" not in summaries

    def test_mostly_nan_values_skipped(self) -> None:
        """Panel with many NaNs → skipped if <10 finite values."""
        # Arrange: Panel with 20 tickers but only 5 finite values
        n = 20
        values = [np.nan] * 15 + [0.1, 0.2, 0.3, 0.4, 0.5]
        data = make_panel(n_tickers=n, signals={"momentum_21d": values})

        # Act
        import pandas as pd

        panel = pd.DataFrame(data)
        summaries = summarize_theme(panel, ["momentum_21d"])

        # Assert: Skipped due to insufficient finite values
        assert "momentum_21d" not in summaries


class TestUnknownPolarity:
    """Test handling of signals with unknown polarity."""

    def test_unknown_polarity_treated_neutral_no_crash(self) -> None:
        """(e) polarity unknown → treated neutral, no crash."""
        # Arrange: Panel with unknown signal
        n = 20
        data = make_panel(
            n_tickers=n,
            signals={"unknown_signal_xyz": rng.standard_normal(n).tolist()},
        )

        # Act: Should not crash
        import pandas as pd

        panel = pd.DataFrame(data)
        summaries = summarize_theme(panel, ["unknown_signal_xyz"])

        # Assert: Treated as neutral, direction is 'neutral'
        assert "unknown_signal_xyz" in summaries
        summary = summaries["unknown_signal_xyz"]
        assert summary.polarity == "neutral"
        assert summary.direction == "neutral"


class TestOptionalColumns:
    """Test handling of optional name and sector columns."""

    def test_name_sector_absent_omitted_from_favored(self) -> None:
        """(f) name/sector optional (absent → omitted from favored)."""
        # Arrange: Panel without name/sector
        n = 15
        data = {
            "ticker": [f"T{i:03d}" for i in range(n)],
            "momentum_21d": [0.5 + i * 0.1 for i in range(n)],
        }

        # Act
        import pandas as pd

        panel = pd.DataFrame(data)
        summaries = summarize_theme(panel, ["momentum_21d"], top_n=2)

        # Assert: name and sector NOT in favored entries
        summary = summaries["momentum_21d"]
        assert "name" not in summary.favored[0]
        assert "sector" not in summary.favored[0]
        assert "ticker" in summary.favored[0]
        assert "value" in summary.favored[0]

    def test_name_present_sector_absent(self) -> None:
        """Only name included."""
        n = 10
        data = {
            "ticker": [f"T{i:03d}" for i in range(n)],
            "name": [f"Company {i}" for i in range(n)],
            "momentum_21d": [0.2 + i * 0.1 for i in range(n)],
        }

        # Act
        import pandas as pd

        panel = pd.DataFrame(data)
        summaries = summarize_theme(panel, ["momentum_21d"], top_n=2)

        # Assert: Only name present, sector absent
        summary = summaries["momentum_21d"]
        assert "name" in summary.favored[0]
        assert "sector" not in summary.favored[0]


class TestDeterminism:
    """Test deterministic behavior."""

    def test_determinism_same_seed_same_result(self) -> None:
        """(g) determinism: same input → same output."""
        # Arrange: Same panel twice
        n = 30
        data = make_panel(
            n_tickers=n,
            signals={"momentum_21d": rng.standard_normal(n).tolist()},
        )

        # Act: Run twice
        import pandas as pd

        panel = pd.DataFrame(data)
        summaries1 = summarize_theme(panel, ["momentum_21d"])
        summaries2 = summarize_theme(panel, ["momentum_21d"])

        # Assert: Identical results
        summary1 = summaries1["momentum_21d"]
        summary2 = summaries2["momentum_21d"]
        assert summary1.direction == summary2.direction
        assert summary1.strength == summary2.strength
        assert summary1.mean == summary2.mean
        assert summary1.favored == summary2.favored


class TestJsonableRoundTrips:
    """Test JSON serialization."""

    def test_jsonable_round_trip(self) -> None:
        """(h) jsonable round-trips: dict → ThemeSignalSummary → jsonable dict."""
        # Arrange: Create a ThemeSignalSummary
        import pandas as pd

        panel = pd.DataFrame(
            make_panel(
                n_tickers=20,
                signals={"momentum_21d": [0.1 + i * 0.05 for i in range(20)]},
            )
        )
        summaries = summarize_theme(panel, ["momentum_21d"], top_n=3)
        original = summaries["momentum_21d"]

        # Act: Convert to jsonable and back
        jsonable = theme_summary_to_jsonable(original)

        # Assert: All fields present and types correct
        assert jsonable["signal"] == "momentum_21d"
        assert jsonable["polarity"] == "bullish_high"
        assert jsonable["direction"] in {"bullish", "bearish", "neutral"}
        assert isinstance(jsonable["strength"], float)
        assert isinstance(jsonable["mean"], float)
        assert isinstance(jsonable["n"], int)
        assert isinstance(jsonable["favored"], list)
        assert len(jsonable["favored"]) == 3
        assert "ticker" in jsonable["favored"][0]
        assert "value" in jsonable["favored"][0]
        assert "name" in jsonable["favored"][0]  # Included by make_panel default

    def test_jsonable_is_json_serializable(self) -> None:
        """jsonable output can be serialized by json.dumps."""
        import json

        import pandas as pd

        # Arrange
        panel = pd.DataFrame(
            make_panel(
                n_tickers=15,
                signals={"volatility_21d": [0.2 + i * 0.03 for i in range(15)]},
            )
        )
        summaries = summarize_theme(panel, ["volatility_21d"], top_n=2)
        summary = summaries["volatility_21d"]

        # Act: Convert to jsonable
        jsonable = theme_summary_to_jsonable(summary)

        # Assert: Can be JSON serialized without error
        json_str = json.dumps(jsonable)
        assert isinstance(json_str, str)
        assert len(json_str) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_signal_list_returns_empty_dict(self) -> None:
        """Empty signal list → empty dict."""
        import pandas as pd

        panel = pd.DataFrame(make_panel(n_tickers=20))
        summaries = summarize_theme(panel, [])
        assert summaries == {}

    def test_missing_signal_column_skipped(self) -> None:
        """Signal column not in panel → skipped without error."""
        import pandas as pd

        panel = pd.DataFrame(make_panel(n_tickers=20, signals={"momentum_21d": [0.1] * 20}))
        summaries = summarize_theme(panel, ["momentum_21d", "missing_signal"])
        assert "momentum_21d" in summaries
        assert "missing_signal" not in summaries

    def test_beta_neutral_polarity(self) -> None:
        """beta_252d has neutral polarity per SIGNAL_POLARITY."""
        import pandas as pd

        panel = pd.DataFrame(
            make_panel(
                n_tickers=20,
                signals={"beta_252d": [0.8 + i * 0.05 for i in range(20)]},
            )
        )
        summaries = summarize_theme(panel, ["beta_252d"])
        summary = summaries["beta_252d"]
        assert summary.polarity == "neutral"
        assert summary.direction == "neutral"  # Always neutral for neutral polarity


class TestFavoredValues:
    """Test favored ticker selection and values."""

    def test_favored_highest_raw_values_for_bullish(self) -> None:
        """For bullish_high, favored = highest raw values."""
        import pandas as pd

        # Arrange: Descending values (ticker 0 = highest)
        n = 10
        values = [1.0 - i * 0.08 for i in range(n)]
        data = make_panel(n_tickers=n, signals={"momentum_21d": values})

        # Act
        panel = pd.DataFrame(data)
        summaries = summarize_theme(panel, ["momentum_21d"], top_n=3)

        # Assert: Favored are highest values (T000, T001, T002)
        summary = summaries["momentum_21d"]
        assert summary.favored[0]["ticker"] == "T000"
        assert summary.favored[0]["value"] == pytest.approx(1.0, rel=0.01)
        assert summary.favored[1]["ticker"] == "T001"
        assert summary.favored[1]["value"] == pytest.approx(0.92, rel=0.01)

    def test_favored_highest_raw_values_for_bearish(self) -> None:
        """For bearish_high, favored STILL = highest raw values (most exposed)."""
        import pandas as pd

        # Arrange: Higher volatility = more bearish exposure
        n = 10
        values = [0.15 + i * 0.05 for i in range(n)]  # T009 has highest vol
        data = make_panel(n_tickers=n, signals={"volatility_21d": values})

        # Act
        panel = pd.DataFrame(data)
        summaries = summarize_theme(panel, ["volatility_21d"], top_n=3)

        # Assert: Favored are highest values (most exposed to bearish signal)
        summary = summaries["volatility_21d"]
        assert summary.favored[0]["ticker"] == "T009"  # Highest vol
        assert summary.favored[0]["value"] == pytest.approx(0.6, rel=0.01)
        assert summary.direction == "bearish"  # High vol is bearish


def test_signal_polarity_documentation() -> None:
    """SIGNAL_POLARITY has documented required signals."""
    # Required signals per spec
    required_bullish = [
        "momentum_21d",
        "momentum_42d",
        "roe",
        "profit_margin",
        "revenue_growth_12m",
        "turnover_21d",
    ]
    required_bearish = [
        "volatility_21d",
        "volatility_63d",
        "leverage",
        "debt_to_equity",
        "amihud_illiquidity_21d",
    ]
    required_neutral = ["beta_252d"]

    # Assert: All required signals present with correct polarity
    for sig in required_bullish:
        assert SIGNAL_POLARITY.get(sig) == "bullish_high", f"{sig} should be bullish_high"

    for sig in required_bearish:
        assert SIGNAL_POLARITY.get(sig) == "bearish_high", f"{sig} should be bearish_high"

    for sig in required_neutral:
        assert SIGNAL_POLARITY.get(sig) == "neutral", f"{sig} should be neutral"


def test_theme_signal_summary_frozen() -> None:
    """ThemeSignalSummary is frozen (immutable)."""
    import pandas as pd

    panel = pd.DataFrame(
        make_panel(
            n_tickers=20,
            signals={"momentum_21d": [0.1 + i * 0.05 for i in range(20)]},
        )
    )
    summaries = summarize_theme(panel, ["momentum_21d"])
    summary = summaries["momentum_21d"]

    # Assert: Frozen dataclass raises on assignment attempt
    with pytest.raises(dataclasses.FrozenInstanceError):
        summary.mean = 999.0  # type: ignore
