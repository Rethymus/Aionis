"""Tests for Jennison-Turnbull group-sequential equivalence gate.

Tests the OBF spending function critical values, reduced confidence intervals,
equivalence verdict logic, and sequential gate stopping behavior.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.eval.sesoi_gate import (
    compute_rci,
    equivalence_verdict,
    look_summary,
    obf_alpha,
    obf_z,
    rci_level,
    sequential_equivalence_gate,
)


class TestOBFValues:
    """Test OBF critical values and derived quantities match frozen spec.

    From ADR-010 amendment (2026-08-01):
        Looks: n ∈ {60, 90, 120} months
        z_α = Φ⁻¹(1−0.05/2) = 1.960
        Iₖ = nₖ/120

        z₁ = 1.960 / √(60/120) = 1.960 / √0.5 = 2.772
        z₂ = 1.960 / √(90/120) = 1.960 / √0.75 = 2.263
        z₃ = 1.960 / √(120/120) = 1.960 / √1 = 1.960

        αₖ = 1−Φ(zₖ)
        α₁ = 0.0028, α₂ = 0.0118, α₃ = 0.0250

        RCI level = 1−2αₖ
        Level 1 = 99.44%, Level 2 = 97.64%, Level 3 = 95.00%
    """

    def test_obf_z_oracle_values(self):
        """Verify zₖ values match frozen specification."""
        z1 = obf_z(1, looks=(60, 90, 120), alpha=0.05)
        z2 = obf_z(2, looks=(60, 90, 120), alpha=0.05)
        z3 = obf_z(3, looks=(60, 90, 120), alpha=0.05)

        # Tolerance of 0.001 for rounding differences
        assert abs(z1 - 2.772) < 0.001, f"Expected z₁≈2.772, got {z1}"
        assert abs(z2 - 2.263) < 0.001, f"Expected z₂≈2.263, got {z2}"
        assert abs(z3 - 1.960) < 0.001, f"Expected z₃≈1.960, got {z3}"

    def test_obf_alpha_oracle_values(self):
        """Verify αₖ values match frozen specification."""
        a1 = obf_alpha(1, looks=(60, 90, 120), alpha=0.05)
        a2 = obf_alpha(2, looks=(60, 90, 120), alpha=0.05)
        a3 = obf_alpha(3, looks=(60, 90, 120), alpha=0.05)

        # Tolerance of 0.0001 for rounding differences
        assert abs(a1 - 0.0028) < 0.0001, f"Expected α₁≈0.0028, got {a1}"
        assert abs(a2 - 0.0118) < 0.0001, f"Expected α₂≈0.0118, got {a2}"
        assert abs(a3 - 0.0250) < 0.0001, f"Expected α₃≈0.0250, got {a3}"

    def test_rci_level_oracle_values(self):
        """Verify RCI confidence levels match frozen specification."""
        l1 = rci_level(1, looks=(60, 90, 120), alpha=0.05)
        l2 = rci_level(2, looks=(60, 90, 120), alpha=0.05)
        l3 = rci_level(3, looks=(60, 90, 120), alpha=0.05)

        # Convert to percentage for clarity
        l1_pct = l1 * 100
        l2_pct = l2 * 100
        l3_pct = l3 * 100

        assert abs(l1_pct - 99.44) < 0.01, f"Expected 99.44%, got {l1_pct:.2f}%"
        assert abs(l2_pct - 97.64) < 0.01, f"Expected 97.64%, got {l2_pct:.2f}%"
        assert abs(l3_pct - 95.00) < 0.01, f"Expected 95.00%, got {l3_pct:.2f}%"

    def test_obf_z_input_validation(self):
        """Verify obf_z validates inputs correctly."""
        with pytest.raises(ValueError, match="k must be in 1..3"):
            obf_z(0, looks=(60, 90, 120))
        with pytest.raises(ValueError, match="k must be in 1..3"):
            obf_z(4, looks=(60, 90, 120))
        with pytest.raises(ValueError, match="alpha must be in \\(0, 1\\)"):
            obf_z(1, alpha=0.0)
        with pytest.raises(ValueError, match="alpha must be in \\(0, 1\\)"):
            obf_z(1, alpha=1.0)

    def test_obf_alpha_input_validation(self):
        """Verify obf_alpha validates inputs correctly."""
        with pytest.raises(ValueError, match="k must be in 1..3"):
            obf_alpha(0, looks=(60, 90, 120))
        with pytest.raises(ValueError, match="alpha must be in \\(0, 1\\)"):
            obf_alpha(1, alpha=0.0)

    def test_rci_level_input_validation(self):
        """Verify rci_level validates inputs correctly."""
        with pytest.raises(ValueError, match="k must be in 1..3"):
            rci_level(0, looks=(60, 90, 120))


class TestRCIAndVerdict:
    """Test reduced confidence interval construction and equivalence verdict."""

    def test_compute_rci_basic(self):
        """Test basic RCI construction."""
        mu = 0.005
        se = 0.010
        z = 2.0

        lo, hi = compute_rci(mu, se, z)

        assert lo == pytest.approx(0.005 - 2.0 * 0.010)
        assert hi == pytest.approx(0.005 + 2.0 * 0.010)

    def test_compute_rci_validation(self):
        """Test compute_rci validates inputs."""
        with pytest.raises(ValueError, match="HAC SE must be positive"):
            compute_rci(0.0, 0.0, 2.0)
        with pytest.raises(ValueError, match="HAC SE must be positive"):
            compute_rci(0.0, -0.001, 2.0)
        with pytest.raises(ValueError, match="z_k must be positive"):
            compute_rci(0.0, 0.010, 0.0)
        with pytest.raises(ValueError, match="z_k must be positive"):
            compute_rci(0.0, 0.010, -1.0)

    def test_equivalence_verdict_inside_margin(self):
        """Test equivalence verdict when RCI is entirely within SESOI."""
        # RCI = [0.002, 0.008] is within [-0.010, +0.010]
        rci = (0.002, 0.008)
        sesoi = 0.010

        result = equivalence_verdict(rci, sesoi)

        assert result["verdict"] == "EQUIVALENT"
        assert result["within_margin"] is True
        assert "⊂" in result["reason"]

    def test_equivalence_verdict_exceeds_upper(self):
        """Test equivalence verdict when RCI exceeds upper bound."""
        # RCI = [0.005, 0.015] exceeds +0.010
        rci = (0.005, 0.015)
        sesoi = 0.010

        result = equivalence_verdict(rci, sesoi)

        assert result["verdict"] == "NOT_EQUIVALENT"
        assert result["within_margin"] is False
        assert "≥ +" in result["reason"]

    def test_equivalence_verdict_exceeds_lower(self):
        """Test equivalence verdict when RCI exceeds lower bound."""
        # RCI = [-0.015, -0.005] exceeds -0.010
        rci = (-0.015, -0.005)
        sesoi = 0.010

        result = equivalence_verdict(rci, sesoi)

        assert result["verdict"] == "NOT_EQUIVALENT"
        assert result["within_margin"] is False
        assert "−0.010" in result["reason"] or "-0.010" in result["reason"]

    def test_equivalence_verdict_strict_containment(self):
        """Test that containment is strict (boundary cases fail)."""
        sesoi = 0.010

        # Exact boundary at upper edge
        rci1 = (0.0, 0.010)
        result1 = equivalence_verdict(rci1, sesoi)
        assert result1["verdict"] == "NOT_EQUIVALENT"

        # Exact boundary at lower edge
        rci2 = (-0.010, 0.0)
        result2 = equivalence_verdict(rci2, sesoi)
        assert result2["verdict"] == "NOT_EQUIVALENT"

    def test_equivalence_verdict_spans_both(self):
        """Test verdict when RCI spans beyond both margins."""
        # RCI = [-0.015, 0.015] spans entire SESOI
        rci = (-0.015, 0.015)
        sesoi = 0.010

        result = equivalence_verdict(rci, sesoi)

        assert result["verdict"] == "NOT_EQUIVALENT"
        assert result["within_margin"] is False
        assert "spans beyond both" in result["reason"]


class TestLookSummary:
    """Test single-look equivalence analysis."""

    @pytest.fixture
    def synthetic_ic_series(self):
        """Create a synthetic IC series for testing."""
        np.random.seed(42)
        n = 120
        # IC values with mean ~0.008 and std ~0.02
        ic = np.random.normal(0.008, 0.02, n)
        return pd.Series(ic, name="rank_ic")

    def test_look_summary_look_1(self, synthetic_ic_series):
        """Test look_summary at look 1 (n=60)."""
        result = look_summary(
            synthetic_ic_series,
            k=1,
            looks=(60, 90, 120),
            sesoi=0.010,
            alpha=0.05,
        )

        assert result["look"] == 1
        assert result["n_obs"] == 60
        assert "mu_hat" in result
        assert "se_hac" in result
        assert result["z_k"] == pytest.approx(2.772, abs=0.001)
        assert result["alpha_k"] == pytest.approx(0.0028, abs=0.0001)
        assert result["rci_level_pct"] == pytest.approx(99.44, abs=0.01)
        assert "rci_lower" in result
        assert "rci_upper" in result
        assert result["verdict"] in ["EQUIVALENT", "NOT_EQUIVALENT"]
        assert "reason" in result

    def test_look_summary_look_2(self, synthetic_ic_series):
        """Test look_summary at look 2 (n=90)."""
        result = look_summary(
            synthetic_ic_series,
            k=2,
            looks=(60, 90, 120),
            sesoi=0.010,
            alpha=0.05,
        )

        assert result["look"] == 2
        assert result["n_obs"] == 90
        assert result["z_k"] == pytest.approx(2.263, abs=0.001)
        assert result["alpha_k"] == pytest.approx(0.0118, abs=0.0001)
        assert result["rci_level_pct"] == pytest.approx(97.64, abs=0.01)

    def test_look_summary_look_3(self, synthetic_ic_series):
        """Test look_summary at look 3 (n=120)."""
        result = look_summary(
            synthetic_ic_series,
            k=3,
            looks=(60, 90, 120),
            sesoi=0.010,
            alpha=0.05,
        )

        assert result["look"] == 3
        assert result["n_obs"] == 120
        assert result["z_k"] == pytest.approx(1.960, abs=0.001)
        assert result["alpha_k"] == pytest.approx(0.0250, abs=0.0001)
        assert result["rci_level_pct"] == pytest.approx(95.00, abs=0.01)

    def test_look_summary_insufficient_obs(self, synthetic_ic_series):
        """Test look_summary with insufficient observations."""
        short_series = synthetic_ic_series.iloc[:30]

        with pytest.raises(ValueError, match="need 60 for look 1"):
            look_summary(short_series, k=1, looks=(60, 90, 120))

    def test_look_summary_invalid_k(self, synthetic_ic_series):
        """Test look_summary with invalid look number."""
        with pytest.raises(ValueError, match="k must be in 1..3"):
            look_summary(synthetic_ic_series, k=0, looks=(60, 90, 120))
        with pytest.raises(ValueError, match="k must be in 1..3"):
            look_summary(synthetic_ic_series, k=4, looks=(60, 90, 120))


class TestSequentialGate:
    """Test the full sequential equivalence gate."""

    @pytest.fixture
    def equivalent_ic_series(self):
        """Create an IC series that achieves equivalence at look 1."""
        np.random.seed(42)
        n = 120
        # Mean = 0.003, very small std → RCI will be within [-0.010, +0.010]
        ic = np.random.normal(0.003, 0.002, n)
        return pd.Series(ic, name="rank_ic")

    @pytest.fixture
    def late_equivalent_ic_series(self):
        """Create an IC series that achieves equivalence only at look 3."""
        np.random.seed(43)
        n = 120
        # Mean = 0.008, moderate std → early looks too wide, look 3 within
        ic = np.random.normal(0.008, 0.008, n)
        return pd.Series(ic, name="rank_ic")

    @pytest.fixture
    def nonequivalent_ic_series(self):
        """Create an IC series that never achieves equivalence."""
        np.random.seed(44)
        n = 120
        # Mean = 0.050, large effect → RCI never within [-0.010, +0.010]
        ic = np.random.normal(0.050, 0.005, n)
        return pd.Series(ic, name="rank_ic")

    def test_sequential_gate_equivalent_look_1(self, equivalent_ic_series):
        """Test gate with IC series that achieves equivalence at look 1."""
        result = sequential_equivalence_gate(
            equivalent_ic_series,
            looks=(60, 90, 120),
            sesoi=0.010,
            alpha=0.05,
        )

        assert result["overall_verdict"] == "EQUIVALENT"
        assert result["stopping_look"] == 1
        assert len(result["looks"]) == 3
        assert result["looks"][0]["verdict"] == "EQUIVALENT"
        assert "Type I error" in result["type_i_control"]

    def test_sequential_gate_nonequivalent(self, nonequivalent_ic_series):
        """Test gate with IC series that never achieves equivalence."""
        result = sequential_equivalence_gate(
            nonequivalent_ic_series,
            looks=(60, 90, 120),
            sesoi=0.010,
            alpha=0.05,
        )

        assert result["overall_verdict"] == "NOT_EQUIVALENT"
        assert result["stopping_look"] is None
        assert len(result["looks"]) == 3
        # All looks should be NOT_EQUIVALENT
        for look_result in result["looks"]:
            assert look_result["verdict"] == "NOT_EQUIVALENT"

    def test_sequential_gate_insufficient_obs(self, nonequivalent_ic_series):
        """Test gate with insufficient observations for final look."""
        short_series = nonequivalent_ic_series.iloc[:60]

        with pytest.raises(ValueError, match="need 120 for final look"):
            sequential_equivalence_gate(short_series, looks=(60, 90, 120))

    def test_sequential_gate_deterministic(self, equivalent_ic_series):
        """Test that gate is deterministic (same input → same output)."""
        result1 = sequential_equivalence_gate(
            equivalent_ic_series,
            looks=(60, 90, 120),
            sesoi=0.010,
            alpha=0.05,
            maxlag=3,
        )
        result2 = sequential_equivalence_gate(
            equivalent_ic_series,
            looks=(60, 90, 120),
            sesoi=0.010,
            alpha=0.05,
            maxlag=3,
        )

        # All values should be identical
        assert result1["overall_verdict"] == result2["overall_verdict"]
        assert result1["stopping_look"] == result2["stopping_look"]
        for r1, r2 in zip(result1["looks"], result2["looks"], strict=True):
            assert r1["mu_hat"] == pytest.approx(r2["mu_hat"])
            assert r1["se_hac"] == pytest.approx(r2["se_hac"])
            assert r1["verdict"] == r2["verdict"]


class TestHandComputedEquivalence:
    """Test with hand-computed synthetic cases for proof of correctness."""

    def test_synthetic_equivalence_case(self):
        """Synthetic case where RCI ⊂ [-0.010, +0.010] → EQUIVALENT."""
        np.random.seed(100)
        n = 120
        # Very small mean and tiny SE → RCI well within margin
        ic = np.random.normal(0.002, 0.001, n)
        ic_series = pd.Series(ic, name="rank_ic")

        result = sequential_equivalence_gate(
            ic_series,
            looks=(60, 90, 120),
            sesoi=0.010,
            alpha=0.05,
        )

        assert result["overall_verdict"] == "EQUIVALENT"
        # Check that at least one look shows strict containment
        found_equivalent = False
        for look in result["looks"]:
            if look["within_margin"]:
                found_equivalent = True
                # Verify strict containment
                assert look["rci_lower"] > -0.010
                assert look["rci_upper"] < 0.010
                break
        assert found_equivalent, "No look achieved equivalence"

    def test_synthetic_nonequivalence_case(self):
        """Synthetic case where RCI ⊄ [-0.010, +0.010] → NOT_EQUIVALENT."""
        np.random.seed(101)
        n = 120
        # Large mean → RCI exceeds upper bound
        ic = np.random.normal(0.080, 0.005, n)
        ic_series = pd.Series(ic, name="rank_ic")

        result = sequential_equivalence_gate(
            ic_series,
            looks=(60, 90, 120),
            sesoi=0.010,
            alpha=0.05,
        )

        assert result["overall_verdict"] == "NOT_EQUIVALENT"
        # All looks should have RCI upper bound >= 0.010
        for look in result["looks"]:
            assert look["rci_upper"] >= 0.010

    def test_synthetic_negative_large_case(self):
        """Synthetic case with large negative mean → NOT_EQUIVALENT."""
        np.random.seed(102)
        n = 120
        # Large negative mean → RCI exceeds lower bound
        ic = np.random.normal(-0.080, 0.005, n)
        ic_series = pd.Series(ic, name="rank_ic")

        result = sequential_equivalence_gate(
            ic_series,
            looks=(60, 90, 120),
            sesoi=0.010,
            alpha=0.05,
        )

        assert result["overall_verdict"] == "NOT_EQUIVALENT"
        # All looks should have RCI lower bound <= -0.010
        for look in result["looks"]:
            assert look["rci_lower"] <= -0.010


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_series(self):
        """Test with empty IC series."""
        ic_series = pd.Series([], name="rank_ic")

        with pytest.raises(ValueError, match="need 120 for final look"):
            sequential_equivalence_gate(ic_series, looks=(60, 90, 120))

    def test_nan_values(self):
        """Test with NaN values in IC series."""
        np.random.seed(103)
        n = 120
        ic = np.random.normal(0.01, 0.02, n)
        ic[10:20] = np.nan  # Introduce NaNs
        ic_series = pd.Series(ic, name="rank_ic")

        # rank_ic_summary drops NaNs, so this should still work
        # but with fewer effective observations
        result = look_summary(ic_series, k=1, looks=(60, 90, 120))
        # Result should be valid (NaNs are dropped)
        assert "mu_hat" in result

    def test_zero_variance_series(self):
        """Test with zero variance in IC series."""
        # All values identical → zero variance
        ic_series = pd.Series([0.01] * 120, name="rank_ic")

        # This should still work but may have HAC SE issues
        result = look_summary(ic_series, k=1, looks=(60, 90, 120))
        # SE might be zero or very small
        assert "mu_hat" in result
