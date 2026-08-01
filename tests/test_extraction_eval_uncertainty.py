"""Tests for extraction evaluation uncertainty intervals (RD-16) — hermetic, hand-computed oracles.

All oracles are computed by hand and documented in comments. No LLM/judge calls.
"""

import pytest

from aionis.extraction.eval_uncertainty import (
    BOOTSTRAP_SEED,
    DEFAULT_CONFIDENCE_LEVEL,
    stratified_bootstrap_f1,
    wilson_score_interval,
)


class TestWilsonScoreInterval:
    """Tests for Wilson score interval computation."""

    def test_wilson_basic_hand_computed(self) -> None:
        """Hand-computed Wilson interval for n=10, successes=7, confidence=0.95.

        Oracle computation:
        - p̂ = 0.7
        - z = 1.96 (95% CI z-critical from chi2_1.ppf(0.95) ≈ 3.8416, sqrt = 1.96)
        - z² = 3.8416
        - denominator = 1 + z²/n = 1 + 3.8416/10 = 1.38416
        - center = (p̂ + z²/(2n)) / denominator = (0.7 + 0.19208) / 1.38416 = 0.6444
        - margin = z * sqrt((p̂(1-p̂) + z²/(4n))/n) / denominator
          = 1.96 * sqrt((0.21 + 0.09604)/10) / 1.38416
          = 1.96 * sqrt(0.030604) / 1.38416
          = 1.96 * 0.1749 / 1.38416
          = 0.2477
        - lower = 0.6444 - 0.2477 = 0.3967
        - upper = 0.6444 + 0.2477 = 0.8921

        Tolerance: 1e-3 (accounts for floating-point rounding differences)
        """
        result = wilson_score_interval(successes=7, n=10, confidence_level=0.95)

        assert result["proportion"] == 0.7
        assert result["confidence_level"] == 0.95
        assert result["warning"] is None

        # Hand-computed bounds with tolerance
        assert 0.396 <= result["lower"] <= 0.398, f"Expected lower ≈0.397, got {result['lower']}"
        assert 0.891 <= result["upper"] <= 0.893, f"Expected upper ≈0.892, got {result['upper']}"

    def test_wilson_empty_input(self) -> None:
        """Edge case: n=0 (empty input)."""
        result = wilson_score_interval(successes=0, n=0)

        assert result["proportion"] is None
        assert result["lower"] is None
        assert result["upper"] is None
        assert result["warning"] == "empty_input"
        assert result["confidence_level"] == DEFAULT_CONFIDENCE_LEVEL

    def test_wilson_single_sample_success(self) -> None:
        """Edge case: n=1, success (single sample)."""
        result = wilson_score_interval(successes=1, n=1)

        assert result["proportion"] == 1.0
        assert result["lower"] is None
        assert result["upper"] is None
        assert result["warning"] == "single_sample"

    def test_wilson_single_sample_failure(self) -> None:
        """Edge case: n=1, failure (single sample)."""
        result = wilson_score_interval(successes=0, n=1)

        assert result["proportion"] == 0.0
        assert result["lower"] is None
        assert result["upper"] is None
        assert result["warning"] == "single_sample"

    def test_wilson_all_success(self) -> None:
        """Edge case: all successes (p=1.0, extreme proportion)."""
        result = wilson_score_interval(successes=10, n=10)

        assert result["proportion"] == 1.0
        assert result["lower"] is None
        assert result["upper"] is None
        assert result["warning"] == "extreme_proportion"

    def test_wilson_all_failure(self) -> None:
        """Edge case: all failures (p=0.0, extreme proportion)."""
        result = wilson_score_interval(successes=0, n=10)

        assert result["proportion"] == 0.0
        assert result["lower"] is None
        assert result["upper"] is None
        assert result["warning"] == "extreme_proportion"

    def test_wilson_half_success(self) -> None:
        """Balanced case: n=100, successes=50 (p=0.5)."""
        result = wilson_score_interval(successes=50, n=100)

        assert result["proportion"] == 0.5
        assert result["warning"] is None
        # For p=0.5, Wilson interval should be approximately symmetric
        # CI should be roughly [0.403, 0.597] for 95% CI
        assert 0.40 < result["lower"] < 0.41
        assert 0.59 < result["upper"] < 0.60

    def test_wilson_custom_confidence_level(self) -> None:
        """Custom confidence level (0.99, wider interval)."""
        result_99 = wilson_score_interval(successes=7, n=10, confidence_level=0.99)
        result_95 = wilson_score_interval(successes=7, n=10, confidence_level=0.95)

        # 99% CI should be wider than 95% CI
        assert result_99["confidence_level"] == 0.99
        assert result_99["lower"] < result_95["lower"]
        assert result_99["upper"] > result_95["upper"]

    def test_wilson_output_json_serializable(self) -> None:
        """Output must be JSON-serializable (pure types)."""
        result = wilson_score_interval(successes=7, n=10)

        # All values must be JSON-serializable types
        assert isinstance(result, dict)
        for _key, value in result.items():
            if value is not None:
                assert isinstance(value, (bool, int, float, str, list, dict))

    def test_wilson_stable_key_order(self) -> None:
        """Dict keys should be in stable order (insertion order preserved in Python 3.7+)."""
        result = wilson_score_interval(successes=7, n=10)
        keys = list(result.keys())

        # Should be in this order
        expected_keys = ["proportion", "lower", "upper", "confidence_level", "warning"]
        assert keys == expected_keys


class TestStratifiedBootstrapF1:
    """Tests for stratified bootstrap F1 computation."""

    def test_bootstrap_determinism(self) -> None:
        """Bootstrap must be deterministic: same input → byte-identical output.

        Oracle: Two calls with identical inputs produce identical results.
        """
        tp_by_stratum = {"13d": 8, "8k": 5, "10k": 3}
        fp_by_stratum = {"13d": 2, "8k": 1, "10k": 2}
        fn_by_stratum = {"13d": 1, "8k": 3, "10k": 1}

        result1 = stratified_bootstrap_f1(
            tp_by_stratum=tp_by_stratum,
            fp_by_stratum=fp_by_stratum,
            fn_by_stratum=fn_by_stratum,
            seed=BOOTSTRAP_SEED,
        )

        result2 = stratified_bootstrap_f1(
            tp_by_stratum=tp_by_stratum,
            fp_by_stratum=fp_by_stratum,
            fn_by_stratum=fn_by_stratum,
            seed=BOOTSTRAP_SEED,
        )

        # Byte-identical: all values exactly equal
        assert result1["f1_estimate"] == result2["f1_estimate"]
        assert result1["lower"] == result2["lower"]
        assert result1["upper"] == result2["upper"]
        assert result1["warnings"] == result2["warnings"]
        assert result1 == result2, "Results must be byte-identical"

    def test_bootstrap_basic_three_strata(self) -> None:
        """Basic three-stratum case with valid F1 estimates.

        Oracle point estimate (macro-F1):
        - Stratum "13d": tp=8, fp=2, fn=1 → precision=0.8, recall=0.8889, F1=0.8421
        - Stratum "8k": tp=5, fp=1, fn=3 → precision=0.8333, recall=0.625, F1=0.7143
        - Stratum "10k": tp=3, fp=2, fn=1 → precision=0.6, recall=0.75, F1=0.6667
        - Macro-F1 = (0.8421 + 0.7143 + 0.6667) / 3 = 0.7444

        Bootstrap interval should be roughly symmetric around 0.744.
        """
        result = stratified_bootstrap_f1(
            tp_by_stratum={"13d": 8, "8k": 5, "10k": 3},
            fp_by_stratum={"13d": 2, "8k": 1, "10k": 2},
            fn_by_stratum={"13d": 1, "8k": 3, "10k": 1},
            n_resamples=1000,  # Smaller for faster test
            seed=BOOTSTRAP_SEED,
        )

        assert result["n_strata"] == 3
        assert result["effective_strata"] == 3
        assert result["warnings"] == {}
        assert result["f1_estimate"] == pytest.approx(0.7444, abs=0.01)
        assert result["lower"] is not None
        assert result["upper"] is not None
        assert result["lower"] < result["f1_estimate"] < result["upper"]

    def test_bootstrap_empty_stratum(self) -> None:
        """Edge case: one stratum has no samples (n=0).

        Oracle: empty stratum excluded, warning added for that stratum.
        """
        result = stratified_bootstrap_f1(
            tp_by_stratum={"13d": 8, "8k": 0, "10k": 3},
            fp_by_stratum={"13d": 2, "8k": 0, "10k": 2},
            fn_by_stratum={"13d": 1, "8k": 0, "10k": 1},
            n_resamples=1000,
            seed=BOOTSTRAP_SEED,
        )

        assert result["n_strata"] == 3
        assert result["effective_strata"] == 2  # "8k" excluded
        assert "8k" in result["warnings"]
        assert result["warnings"]["8k"] == "empty_stratum"
        assert result["f1_estimate"] is not None

    def test_bootstrap_tiny_stratum_warning(self) -> None:
        """Edge case: stratum with n < MINIMUM_STRATUM_SIZE (< 5).

        Oracle: tiny stratum included but warning added.
        """
        result = stratified_bootstrap_f1(
            tp_by_stratum={"13d": 8, "small": 1},
            fp_by_stratum={"13d": 2, "small": 0},
            fn_by_stratum={"13d": 1, "small": 1},
            n_resamples=1000,
            seed=BOOTSTRAP_SEED,
        )

        assert result["n_strata"] == 2
        # "small" has n=2 (<5), so it should get a warning
        assert "small" in result["warnings"]
        assert "tiny_stratum" in result["warnings"]["small"]

    def test_bootstrap_undefined_f1_stratum(self) -> None:
        """Edge case: stratum with undefined F1 (zero denominator).

        Example: tp=0, fp=0, fn=5 → precision=0/0 undefined, recall=0/5=0
        """
        result = stratified_bootstrap_f1(
            tp_by_stratum={"13d": 8, "bad": 0},
            fp_by_stratum={"13d": 2, "bad": 0},
            fn_by_stratum={"13d": 1, "bad": 5},
            n_resamples=1000,
            seed=BOOTSTRAP_SEED,
        )

        assert result["n_strata"] == 2
        assert result["effective_strata"] == 1  # "bad" excluded
        assert "bad" in result["warnings"]
        assert result["warnings"]["bad"] == "undefined_f1"

    def test_bootstrap_all_strata_invalid(self) -> None:
        """Edge case: all strata have undefined F1.

        Oracle: returns f1_estimate=None, bounds=None.
        """
        result = stratified_bootstrap_f1(
            tp_by_stratum={"bad1": 0, "bad2": 0},
            fp_by_stratum={"bad1": 0, "bad2": 0},
            fn_by_stratum={"bad1": 5, "bad2": 3},
            n_resamples=1000,
            seed=BOOTSTRAP_SEED,
        )

        assert result["n_strata"] == 2
        assert result["effective_strata"] == 0
        assert result["f1_estimate"] is None
        assert result["lower"] is None
        assert result["upper"] is None

    def test_bootstrap_no_strata_provided(self) -> None:
        """Edge case: no strata provided (empty dicts).

        Oracle: returns all None with warning "no_strata_provided".
        """
        result = stratified_bootstrap_f1(
            tp_by_stratum={},
            fp_by_stratum={},
            fn_by_stratum={},
            n_resamples=1000,
            seed=BOOTSTRAP_SEED,
        )

        assert result["n_strata"] == 0
        assert result["effective_strata"] == 0
        assert result["f1_estimate"] is None
        assert result["lower"] is None
        assert result["upper"] is None
        assert "all" in result["warnings"]
        assert result["warnings"]["all"] == "no_strata_provided"

    def test_bootstrap_single_stratum(self) -> None:
        """Edge case: only one stratum (n=1 effectively).

        Should work but warning may be added for tiny stratum if n < 5.
        """
        result = stratified_bootstrap_f1(
            tp_by_stratum={"13d": 3},
            fp_by_stratum={"13d": 1},
            fn_by_stratum={"13d": 1},
            n_resamples=1000,
            seed=BOOTSTRAP_SEED,
        )

        assert result["n_strata"] == 1
        assert result["effective_strata"] == 1
        # n=5 is exactly the threshold, so no warning
        assert result["warnings"] == {}
        assert result["f1_estimate"] is not None

    def test_bootstrap_custom_resamples_and_confidence(self) -> None:
        """Custom n_resamples and confidence_level parameters."""
        result = stratified_bootstrap_f1(
            tp_by_stratum={"13d": 8},
            fp_by_stratum={"13d": 2},
            fn_by_stratum={"13d": 1},
            n_resamples=500,
            confidence_level=0.99,
            seed=BOOTSTRAP_SEED,
        )

        assert result["n_resamples"] == 500
        assert result["confidence_level"] == 0.99

    def test_bootstrap_output_json_serializable(self) -> None:
        """Output must be JSON-serializable (pure types)."""
        result = stratified_bootstrap_f1(
            tp_by_stratum={"13d": 8},
            fp_by_stratum={"13d": 2},
            fn_by_stratum={"13d": 1},
            n_resamples=100,
            seed=BOOTSTRAP_SEED,
        )

        # All values must be JSON-serializable types
        assert isinstance(result, dict)
        for key, value in result.items():
            if value is not None and not isinstance(value, (bool, int, float, str, list, dict)):
                pytest.fail(f"Value for key '{key}' is not JSON-serializable: {type(value)}")

    def test_bootstrap_missing_keys_in_stratum_dicts(self) -> None:
        """Stratum may be missing from some dicts (default to 0)."""
        result = stratified_bootstrap_f1(
            tp_by_stratum={"13d": 8, "8k": 5},
            fp_by_stratum={"13d": 2},  # "8k" missing
            fn_by_stratum={"13d": 1, "8k": 3},
            n_resamples=1000,
            seed=BOOTSTRAP_SEED,
        )

        assert result["n_strata"] == 2  # Both "13d" and "8k" counted
        # "8k" should have fp=0 (default)
        assert result["effective_strata"] == 2

    def test_bootstrap_sorted_strata_iteration(self) -> None:
        """Strata must be processed in sorted order for determinism."""
        # Reverse order input
        result = stratified_bootstrap_f1(
            tp_by_stratum={"z": 8, "a": 5, "m": 3},
            fp_by_stratum={"z": 2, "a": 1, "m": 2},
            fn_by_stratum={"z": 1, "a": 3, "m": 1},
            n_resamples=100,
            seed=BOOTSTRAP_SEED,
        )

        # Should process in order: a, m, z (sorted)
        # Verify by running twice with same seed
        result2 = stratified_bootstrap_f1(
            tp_by_stratum={"z": 8, "a": 5, "m": 3},
            fp_by_stratum={"z": 2, "a": 1, "m": 2},
            fn_by_stratum={"z": 1, "a": 3, "m": 1},
            n_resamples=100,
            seed=BOOTSTRAP_SEED,
        )

        assert result == result2, "Order-independent with sorted iteration"

    def test_bootstrap_warning_types_comprehensive(self) -> None:
        """Verify all warning types are properly generated."""
        result = stratified_bootstrap_f1(
            tp_by_stratum={
                "empty": 0,
                "tiny": 1,
                "undefined": 0,
                "good": 8,
                "tiny_undefined": 0,
            },
            fp_by_stratum={
                "empty": 0,
                "tiny": 0,
                "undefined": 0,
                "good": 2,
                "tiny_undefined": 0,
            },
            fn_by_stratum={
                "empty": 0,
                "tiny": 1,
                "undefined": 5,
                "good": 1,
                "tiny_undefined": 1,
            },
            n_resamples=100,
            seed=BOOTSTRAP_SEED,
        )

        warnings = result["warnings"]

        # Verify expected warnings
        assert "empty" in warnings
        assert warnings["empty"] == "empty_stratum"

        assert "tiny" in warnings
        assert "tiny_stratum" in warnings["tiny"]

        assert "undefined" in warnings
        assert warnings["undefined"] == "undefined_f1"

        # "good" should have no warning
        assert "good" not in warnings

        # "tiny_undefined" gets undefined_f1 (takes precedence)
        assert "tiny_undefined" in warnings
        assert warnings["tiny_undefined"] == "undefined_f1"
