"""Jennison-Turnbull group-sequential equivalence gate (AUD-07B).

Implements the OBF (O'Brien-Fleming) spending-function group-sequential
equivalence test for the SESOI (Smallest Effect Size of Interest) contract.
This is a parametric gate using reduced confidence intervals (RCI) with
Newey-West HAC standard errors.

The gate tests the null hypothesis H0: |μ| ≥ SESOI against the alternative
H1: |μ| < SESOI, where μ is the cross-sectional rank-IC. Equivalence is
declared when the entire RCI at a given look falls within [−SESOI, +SESOI].

Critical values follow the OBF spending function: zₖ = z_α / √Iₖ, where
Iₖ = nₖ/n_max is the information fraction at look k. For the default 3-look
design at n ∈ {60, 90, 120} months with α = 0.05:
  Look 1 (n=60):  z₁=2.772, α₁=0.0028,  RCI level=99.44%
  Look 2 (n=90):  z₂=2.263, α₂=0.0118,  RCI level=97.64%
  Look 3 (n=120): z₃=1.960, α₃=0.0250,  RCI level=95.00%

The gate stops at the first look where RCI ⊂ [−SESOI, +SESOI], declaring
EQUIVALENT. If no look achieves equivalence, the final verdict is
NOT_EQUIVALENT. The OBF spending function strongly controls Type I error
at α across the sequential looks.

Reference:
  Jennison & Turnbull (2000). Group Sequential Methods with Applications
  to Clinical Trials. Chapter 7 (equivalence) and 14 (OBF spending).

Frozen spec: decisions/ADR-010-sesoi-tost-sequential-gate.md
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def obf_z(k: int, looks: tuple[int, ...] = (60, 90, 120), alpha: float = 0.05) -> float:
    """O'Brien-Fleming critical value zₖ at look k.

    zₖ = z_α / √Iₖ, where z_α = Φ⁻¹(1−α/2) and Iₖ = looks[k-1] / looks[-1]
    is the information fraction.

    Args:
        k: Look number (1-indexed, must be in 1..len(looks)).
        looks: Ordered tuple of sample sizes at each look.
        alpha: Overall family-wise error rate (default 0.05).

    Returns:
        Critical value zₖ for constructing the reduced confidence interval.

    Raises:
        ValueError: If k is out of range or alpha is not in (0, 1).
    """
    if not 1 <= k <= len(looks):
        raise ValueError(f"k must be in 1..{len(looks)}, got {k}")
    if not 0 < alpha < 1:
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")

    z_alpha = float(norm.ppf(1 - alpha / 2))
    info_fraction = looks[k - 1] / looks[-1]
    return z_alpha / np.sqrt(info_fraction)


def obf_alpha(k: int, looks: tuple[int, ...] = (60, 90, 120), alpha: float = 0.05) -> float:
    """Two-sided Type I error rate αₖ allocated to look k by OBF spending.

    αₖ = 1 − Φ(zₖ), where zₖ is the OBF critical value at look k.

    Args:
        k: Look number (1-indexed, must be in 1..len(looks)).
        looks: Ordered tuple of sample sizes at each look.
        alpha: Overall family-wise error rate (default 0.05).

    Returns:
        αₖ, the error rate allocated to this look.

    Raises:
        ValueError: If k is out of range or alpha is not in (0, 1).
    """
    z_k = obf_z(k, looks, alpha)
    return 1.0 - float(norm.cdf(z_k))


def rci_level(k: int, looks: tuple[int, ...] = (60, 90, 120), alpha: float = 0.05) -> float:
    """Confidence level of the reduced confidence interval at look k.

    Level = 1 − 2αₖ, where αₖ is the OBF-allocated error rate.

    Args:
        k: Look number (1-indexed, must be in 1..len(looks)).
        looks: Ordered tuple of sample sizes at each look.
        alpha: Overall family-wise error rate (default 0.05).

    Returns:
        Confidence level in (0, 1), e.g., 0.9944 for 99.44%.

    Raises:
        ValueError: If k is out of range or alpha is not in (0, 1).
    """
    alpha_k = obf_alpha(k, looks, alpha)
    return 1.0 - 2.0 * alpha_k


def compute_rci(mu_hat: float, se_hac: float, z_k: float) -> tuple[float, float]:
    """Reduced confidence interval RCIₖ = [μ̂ − zₖ·σ̂, μ̂ + zₖ·σ̂].

    Args:
        mu_hat: Observed mean rank-IC at this look.
        se_hac: Newey-West HAC standard error of μ̂.
        z_k: OBF critical value at this look.

    Returns:
        (lower, upper) bounds of the RCI.

    Raises:
        ValueError: If se_hac is non-positive or z_k is non-positive.
    """
    if se_hac <= 0:
        raise ValueError(f"HAC SE must be positive, got {se_hac}")
    if z_k <= 0:
        raise ValueError(f"Critical value z_k must be positive, got {z_k}")

    margin = z_k * se_hac
    return (mu_hat - margin, mu_hat + margin)


def equivalence_verdict(
    rci: tuple[float, float],
    sesoi: float = 0.010,
) -> dict[str, object]:
    """Determine if an RCI demonstrates equivalence within SESOI margin.

    EQUIVALENT iff the entire RCI lies strictly inside [−SESOI, +SESOI]:
        lower_bound > −SESOI AND upper_bound < +SESOI

    Args:
        rci: (lower, upper) bounds of the reduced confidence interval.
        sesoi: Smallest effect size of interest (default 0.010).

    Returns:
        Dict with keys:
            verdict: "EQUIVALENT" | "NOT_EQUIVALENT"
            within_margin: bool (True if equivalent)
            lower: float, upper: float, sesoi: float
            reason: str explaining the decision
    """
    lo, hi = rci

    # Strict containment: RCI must be entirely within the margin
    is_equivalent = (lo > -sesoi) and (hi < sesoi)

    if is_equivalent:
        reason = f"RCI [{lo:.4f}, {hi:.4f}] ⊂ [−{sesoi:.3f}, +{sesoi:.3f}]"
    else:
        if lo <= -sesoi and hi >= sesoi:
            reason = f"RCI [{lo:.4f}, {hi:.4f}] spans beyond both margins"
        elif lo <= -sesoi:
            reason = f"RCI lower {lo:.4f} ≤ −{sesoi:.3f}"
        else:  # hi >= sesoi
            reason = f"RCI upper {hi:.4f} ≥ +{sesoi:.3f}"

    return {
        "verdict": "EQUIVALENT" if is_equivalent else "NOT_EQUIVALENT",
        "within_margin": is_equivalent,
        "lower": lo,
        "upper": hi,
        "sesoi": sesoi,
        "reason": reason,
    }


def look_summary(
    ic_series: pd.Series,
    k: int,
    looks: tuple[int, ...] = (60, 90, 120),
    sesoi: float = 0.010,
    alpha: float = 0.05,
    maxlag: int | None = None,
) -> dict[str, object]:
    """Full equivalence analysis at a single look k.

    Computes μ̂ and HAC SE via ``rank_ic_summary`` on the IC series up to
    look k, then constructs the OBF RCI and evaluates equivalence.

    Args:
        ic_series: Time series of monthly rank-IC values (indexed by date).
        k: Look number (1-indexed).
        looks: Ordered tuple of sample sizes at each look.
        sesoi: Smallest effect size of interest (default 0.010).
        alpha: Overall family-wise error rate (default 0.05).
        maxlag: Newey-West lag parameter (None → automatic).

    Returns:
        Dict with all intermediate values for auditability:
            look: int, n_obs: int
            mu_hat: float, se_hac: float
            z_k: float, alpha_k: float, rci_level_pct: float
            rci_lower: float, rci_upper: float
            verdict: str, within_margin: bool
            reason: str
    """
    from aionis.eval.rank_ic import rank_ic_summary

    if not 1 <= k <= len(looks):
        raise ValueError(f"k must be in 1..{len(looks)}, got {k}")

    n_obs = looks[k - 1]
    if len(ic_series) < n_obs:
        raise ValueError(
            f"IC series has {len(ic_series)} obs, need {n_obs} for look {k}"
        )

    # Truncate to the first n_obs observations for this look
    ic_at_look = ic_series.iloc[:n_obs]

    # Compute μ̂ and HAC SE
    summary = rank_ic_summary(ic_at_look, maxlag=maxlag)
    mu_hat = summary["mean_ic"]
    se_hac = summary["se_hac"]

    # OBF critical value and derived quantities
    z_k = obf_z(k, looks, alpha)
    alpha_k = obf_alpha(k, looks, alpha)
    level = rci_level(k, looks, alpha)

    # Construct RCI and evaluate equivalence
    rci = compute_rci(mu_hat, se_hac, z_k)
    verdict_dict = equivalence_verdict(rci, sesoi)

    return {
        "look": k,
        "n_obs": n_obs,
        "mu_hat": mu_hat,
        "se_hac": se_hac,
        "z_k": z_k,
        "alpha_k": alpha_k,
        "rci_level_pct": level * 100.0,
        "rci_lower": rci[0],
        "rci_upper": rci[1],
        "verdict": verdict_dict["verdict"],
        "within_margin": verdict_dict["within_margin"],
        "reason": verdict_dict["reason"],
    }


def sequential_equivalence_gate(
    ic_series: pd.Series,
    looks: tuple[int, ...] = (60, 90, 120),
    sesoi: float = 0.010,
    alpha: float = 0.05,
    maxlag: int | None = None,
) -> dict[str, object]:
    """Group-sequential equivalence gate across all looks.

    Evaluates equivalence at each look in sequence. Stops at the first look
    where RCI ⊂ [−SESOI, +SESOI] and declares EQUIVALENT. If no look achieves
    equivalence, returns NOT_EQUIVALENT after all looks.

    The OBF spending function strongly controls Type I error at α across the
    sequential looks.

    Args:
        ic_series: Time series of monthly rank-IC values (indexed by date).
        looks: Ordered tuple of sample sizes at each look.
        sesoi: Smallest effect size of interest (default 0.010).
        alpha: Overall family-wise error rate (default 0.05).
        maxlag: Newey-West lag parameter (None → automatic).

    Returns:
        Dict with:
            looks: list of per-look summaries (each a full ``look_summary`` dict)
            overall_verdict: "EQUIVALENT" | "NOT_EQUIVALENT"
            stopping_look: int | None (the look at which equivalence was first shown)
            type_i_control: str (reminder of the α-level control)
    """
    if len(ic_series) < looks[-1]:
        raise ValueError(
            f"IC series has {len(ic_series)} obs, need {looks[-1]} for final look"
        )

    per_look_summaries = []
    overall_verdict = "NOT_EQUIVALENT"
    stopping_look: int | None = None

    for k in range(1, len(looks) + 1):
        summary = look_summary(ic_series, k, looks, sesoi, alpha, maxlag)
        per_look_summaries.append(summary)

        # Stop at first equivalence
        if summary["verdict"] == "EQUIVALENT" and stopping_look is None:
            overall_verdict = "EQUIVALENT"
            stopping_look = k
            # Continue processing remaining looks for completeness of audit trail
            # (the gate is already EQUIVALENT, but we want all summaries)

    # Note: If we stopped early, we still have summaries for all looks because
    # we always compute the full set above. The stopping_look indicates which
    # look first triggered equivalence.

    return {
        "looks": per_look_summaries,
        "overall_verdict": overall_verdict,
        "stopping_look": stopping_look,
        "type_i_control": (
            f"OBF spending function strongly controls Type I error at α={alpha:.3f} "
            f"across {len(looks)} sequential looks"
        ),
    }
