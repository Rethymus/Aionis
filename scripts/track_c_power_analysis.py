#!/usr/bin/env python3
"""Track C prospective power analysis — is the frozen J-T look schedule adequate?

The confirmatory run (ledger #49) returned J-T look-1 NOT_EQUIVALENT: the 99.44%
RCI [-0.051, +0.027] is far wider than the +/-0.010 SESOI. This script asks the
follow-up question: **can the planned looks 2 (n=90) / 3 (n=120) realistically
declare equivalence given the observed monthly rank-IC noise?**

Method (all derived from the confirmatory run's ``combined_ic_series``):
  1. Empirical sigma + lag-1 autocorrelation of the monthly IC series.
  2. Analytic HAC-SE scaling: se(n) calibrated to the observed se_hac at n=71,
     then projected to n = 60, 90, 120, 200, 432.
  3. RCI half-width at each look's OBF z_k (2.772 / 2.263 / 1.960).
  4. Minimum n for equivalence declaration (RCI half < SESOI assuming true mean=0).
  5. Block bootstrap (block=12 months, preserves autocorrelation): resample the
     IC series to each target n, compute the look-k RCI, check strict-containment
     within +/-0.010. Repeat 2000x -> P(equivalence | empirical IC distribution).

This is a DESIGN ASSESSMENT of frozen #48's look schedule + SESOI. It changes NO
frozen surface / ledger / config. It informs: (a) whether E3 forward-live can
realistically reach equivalence at look-2/3, (b) whether a future amendment
should widen SESOI or extend the look horizon.

Run::

    uv run python scripts/track_c_power_analysis.py
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from aionis.config import settings
from aionis.eval.sesoi_gate import obf_z

IC_SERIES_PATH = settings.data_dir.parent / "runs" / "track_c_confirmatory_ic_series.parquet"
OUT_PATH = settings.data_dir.parent / "runs" / "track_c_confirmatory_power_analysis.json"

LOOKS = (60, 90, 120)
SESOI = 0.010
ALPHA = 0.05
N_BOOTSTRAP = 2000
BLOCK_MONTHS = 12  # circular block bootstrap block size (preserves autocorrelation)
RNG_SEED = 0  # H6 spirit: pinned seed


def _load_combined_ic() -> pd.Series:
    df = pd.read_parquet(IC_SERIES_PATH)
    if "combined" not in df.columns:
        raise SystemExit(f"[ERROR] {IC_SERIES_PATH} has no 'combined' column: {df.columns}")
    s = df["combined"].dropna().sort_index()
    if len(s) < LOOKS[0]:
        raise SystemExit(f"[ERROR] IC series has {len(s)} obs, need >= {LOOKS[0]}")
    return s


def _lag1_autocorrelation(s: pd.Series) -> float:
    x = s.to_numpy(dtype=float)
    x = x - x.mean()
    denom = float(np.sum(x * x))
    if denom <= 0:
        return 0.0
    return float(np.sum(x[:-1] * x[1:]) / denom)


def _analytic_se(sigma: float, rho: float, n: int) -> float:
    """HAC SE of the mean under AR(1)-ish autocorrelation: sigma/sqrt(n) * sqrt((1+rho)/(1-rho)).

    Calibrated so that analytic_se at the observed n reproduces the observed se_hac.
    """
    ar1_factor = np.sqrt((1.0 + rho) / max(1e-9, 1.0 - rho))
    return sigma * ar1_factor / np.sqrt(n)


def _block_bootstrap_power(
    ic: np.ndarray, n_target: int, z_k: float, sesoi: float = SESOI,
    n_boot: int = N_BOOTSTRAP, seed: int = RNG_SEED,
) -> dict:
    """Circular block bootstrap: P(RCI_k strictly inside +/-sesoi | empirical IC).

    Resample n_target months (in blocks of BLOCK_MONTHS, circular) from the
    observed IC series, compute the sample mean + HAC SE (Newey-West, auto maxlag),
    build RCI = mean +/- z_k*se, check strict-containment within +/-sesoi.
    """
    rng = np.random.default_rng(seed)
    n_pop = len(ic)
    n_blocks_needed = int(np.ceil(n_target / BLOCK_MONTHS))
    equiv_count = 0
    rci_halfs = []
    for _ in range(n_boot):
        start_idxs = rng.integers(0, n_pop, size=n_blocks_needed)
        sample = np.concatenate(
            [ic[s : s + BLOCK_MONTHS] for s in start_idxs]
        )[:n_target]
        mean = float(np.mean(sample))
        # Newey-West HAC SE of the mean (auto maxlag rule)
        maxlag = max(1, int(4 * (n_target / 100.0) ** (2 / 9)))
        se = _nw_se(sample, maxlag)
        if not np.isfinite(se) or se <= 0:
            continue
        rci_half = z_k * se
        rci_halfs.append(rci_half)
        # strict-containment: |mean| + rci_half < sesoi
        if abs(mean) + rci_half < sesoi:
            equiv_count += 1
    rci_halfs = np.array(rci_halfs) if rci_halfs else np.array([float("nan")])
    return {
        "n_target": n_target,
        "n_boot_valid": int(len(rci_halfs)),
        "p_equivalence": equiv_count / max(1, len(rci_halfs)),
        "rci_half_median": float(np.median(rci_halfs)),
        "rci_half_p05": float(np.percentile(rci_halfs, 5)),
        "rci_half_p95": float(np.percentile(rci_halfs, 95)),
    }


def _nw_se(x: np.ndarray, maxlag: int) -> float:
    """Newey-West HAC SE of the mean of series x."""
    n = len(x)
    x = x - x.mean()
    gamma0 = float(np.sum(x * x) / n)
    var = gamma0
    for lag in range(1, maxlag + 1):
        gamma_lag = float(np.sum(x[:-lag] * x[lag:]) / n)
        var += 2.0 * (1.0 - lag / (maxlag + 1)) * gamma_lag
    return float(np.sqrt(var / n))


def _min_n_for_equivalence(sigma: float, rho: float, z_k: float, sesoi: float = SESOI) -> float:
    """Min n so that analytic RCI half-width < sesoi (true mean=0)."""
    ar1_factor = np.sqrt((1.0 + rho) / max(1e-9, 1.0 - rho))
    # z_k * sigma * ar1_factor / sqrt(n) < sesoi  =>  n > (z_k*sigma*ar1_factor/sesoi)^2
    return float((z_k * sigma * ar1_factor / sesoi) ** 2)


def main() -> int:
    ic = _load_combined_ic()
    ic_arr = ic.to_numpy(dtype=float)
    n_obs = len(ic_arr)
    sigma = float(np.std(ic_arr, ddof=1))
    rho = _lag1_autocorrelation(ic)
    mean_ic = float(np.mean(ic_arr))

    print(
        f"[power] loaded combined_ic: n={n_obs} mean={mean_ic:.6f} "
        f"sigma={sigma:.6f} lag1_rho={rho:.4f}"
    )

    # Calibrate analytic SE to the observed se_hac at n_obs (from ledger #49: 0.012625).
    # The AR(1)-style formula has an implicit sigma_eff; back out sigma_eff from observed se.
    OBSERVED_SE_HAC = 0.012625  # ledger #49 combined_ic.se_hac
    ar1_factor = np.sqrt((1.0 + rho) / max(1e-9, 1.0 - rho))
    sigma_eff = OBSERVED_SE_HAC * np.sqrt(n_obs) / ar1_factor
    print(
        f"[power] calibrated sigma_eff={sigma_eff:.6f} "
        f"(from observed se_hac={OBSERVED_SE_HAC} at n={n_obs})"
    )

    print("\n=== Analytic RCI half-widths (true mean=0) ===")
    analytic = []
    for k, n_k in enumerate(LOOKS, start=1):
        z_k = float(obf_z(k, LOOKS, ALPHA))
        se = _analytic_se(sigma_eff, rho, n_k)
        rci_half = z_k * se
        n_min = _min_n_for_equivalence(sigma_eff, rho, z_k)
        verdict = "EQUIVALENT-feasible" if rci_half < SESOI else "NOT_EQUIVALENT (RCI too wide)"
        analytic.append({
            "look": k, "n_planned": n_k, "z_k": round(z_k, 3),
            "se_projected": round(se, 5), "rci_half": round(rci_half, 5),
            "sesoi": SESOI, "n_min_for_equivalence": round(n_min, 0),
            "verdict_at_true_zero": verdict,
        })
        print(
            f"  look-{k} (n={n_k}, z={z_k:.3f}): se={se:.5f} RCI_half={rci_half:.5f} "
            f"vs SESOI={SESOI} -> {verdict}; n_min={n_min:.0f} months"
        )

    print("\n=== Min n for equivalence at each look's z (true |IC|=0) ===")
    for k in range(1, len(LOOKS) + 1):
        z_k = float(obf_z(k, LOOKS, ALPHA))
        n_min = _min_n_for_equivalence(sigma_eff, rho, z_k)
        print(f"  look-{k} (z={z_k:.3f}): n_min={n_min:.0f} months ({n_min/12:.1f} years)")

    print(f"\n=== Block bootstrap P(equivalence | empirical IC, n_boot={N_BOOTSTRAP}) ===")
    bootstrap = []
    for k, n_k in enumerate(LOOKS, start=1):
        z_k = float(obf_z(k, LOOKS, ALPHA))
        b = _block_bootstrap_power(ic_arr, n_k, z_k)
        bootstrap.append(b)
        print(
            f"  look-{k} (n={n_k}): P(equiv)={b['p_equivalence']:.4f} "
            f"RCI_half med={b['rci_half_median']:.5f} "
            f"[p05={b['rci_half_p05']:.5f}, p95={b['rci_half_p95']:.5f}]"
        )

    # Also project an extended horizon to show the timeline to feasibility.
    print("\n=== Extended: analytic RCI half-width at larger n (look-3 z=1.960) ===")
    z3 = float(obf_z(3, LOOKS, ALPHA))
    extended = []
    for n_ext in (120, 180, 240, 360, 432):
        se = _analytic_se(sigma_eff, rho, n_ext)
        rci_half = z3 * se
        extended.append({"n": n_ext, "se": round(se, 5), "rci_half": round(rci_half, 5),
                         "within_sesoi": bool(rci_half < SESOI)})
        tag = "< SESOI" if rci_half < SESOI else ">= SESOI"
        print(f"  n={n_ext} ({n_ext/12:.0f}y): se={se:.5f} RCI_half={rci_half:.5f} {tag}")

    out = {
        "source": "track_c_confirmatory_ic_series (ledger #49)",
        "n_observed": n_obs,
        "mean_ic": mean_ic,
        "sigma_ic": sigma,
        "lag1_autocorrelation": rho,
        "calibrated_sigma_eff": sigma_eff,
        "observed_se_hac_at_n71": OBSERVED_SE_HAC,
        "sesoi": SESOI,
        "alpha": ALPHA,
        "analytic_looks": analytic,
        "bootstrap_looks": bootstrap,
        "extended_horizon_look3_z": extended,
        "interpretation": (
            "If analytic RCI half-width at a look exceeds SESOI (with true mean=0), "
            "equivalence is structurally infeasible at that look regardless of the "
            "observed mean. n_min_for_equivalence = months of data needed for the "
            "RCI to fit within +/-SESOI at that look's OBF z. Bootstrap P(equiv) is "
            "the empirical probability of declaring equivalence under the observed "
            "IC distribution (which embeds the observed mean)."
        ),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\n[power] saved -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
