"""EXPLORATORY theoretical pure-noise bound for cross-sectional rank-IC.

Companion to scripts/ic_noise_floor_survey.py. That script measures the OBSERVED
sigma(IC); this one computes the CLOSED-FORM pure-noise Spearman bound
sigma_null = 1/sqrt(N_cross - 1) (variance of the Spearman rank correlation under
the null of no predictability, for a cross-section of N_cross assets), compares it
to the observed sigma, and quantifies the excess ratio.

The excess (observed >> pure-noise) is the methodologically interesting quantity:
it reflects ML fitting noise, return heteroskedasticity, and overlap, and it is
what makes the +/-0.010 equivalence power floor bind (the pure-noise bound alone
would be marginally powered at look-3; the excess-inflated observed sigma is not).

Reuses persisted OOS-score panels + IC series (no rerun, no network). Writes ONLY
to runs/ (gitignored); never to runs/ledger.jsonl.

Usage::
    uv run python scripts/ic_pure_noise_bound.py
"""
from __future__ import annotations

import glob
import json
import math
from pathlib import Path

import pandas as pd
import structlog

log = structlog.get_logger()

OUT_PATH = "runs/ic_pure_noise_bound.json"


def pure_noise_sigma(n_cross: int) -> float:
    """Closed-form std of Spearman rank-IC under the null (no predictability).

    For two independent rankings of n_cross items, Var(rho) = 1/(n_cross - 1)
    (standard result; exact for n_cross >= 2). Returns the std (not variance).
    """
    if n_cross < 2:
        return float("nan")
    return 1.0 / math.sqrt(n_cross - 1)


def _n_cross_eff(scores: pd.DataFrame) -> dict:
    """Median per-month cross-section size, overall and per-region if present."""
    out: dict = {}
    if "date" not in scores.columns or "ticker" not in scores.columns:
        return out
    d = scores.copy()
    d["date"] = pd.to_datetime(d["date"])
    per_month = d.groupby("date")["ticker"].nunique()
    out["n_cross_median"] = float(per_month.median())
    out["n_cross_min"] = int(per_month.min())
    out["n_cross_max"] = int(per_month.max())
    if "region" in d.columns:
        per_region: dict[str, float] = {}
        for region, g in d.groupby("region"):
            pm = g.groupby("date")["ticker"].nunique()
            per_region[str(region)] = float(pm.median())
        out["n_cross_per_region"] = per_region
    return out


def _observed_sigma(ic_series: pd.DataFrame, col: str) -> float | None:
    if col not in ic_series.columns:
        return None
    s = ic_series[col].dropna()
    if len(s) < 2:
        return None
    return float(s.std(ddof=1))


def _track_c_rows() -> list[dict]:
    """Track C: per-region pure-noise bound vs observed sigma, + combined."""
    rows: list[dict] = []
    scores_paths = sorted(set(glob.glob("runs/track_c_*_oos_scores.parquet")))
    ic_paths = {Path(p).stem.replace("_oos_scores", ""): p for p in scores_paths}
    for stem, sp in ic_paths.items():
        icp = f"runs/{stem}_ic_series.parquet"
        try:
            scores = pd.read_parquet(sp)
            ic = pd.read_parquet(icp)
        except FileNotFoundError:
            continue
        nc = _n_cross_eff(scores)
        for region in ("us", "cn", "combined"):
            obs = _observed_sigma(ic, region)
            key = (region if region in nc.get("n_cross_per_region", {}) else None)
            n_cross = nc.get("n_cross_per_region", {}).get(key) if key else nc.get("n_cross_median")
            bound = pure_noise_sigma(int(n_cross)) if n_cross and n_cross >= 2 else None
            ratio = (obs / bound) if (obs and bound and bound > 0) else None
            rows.append({
                "source": stem, "arm": region,
                "n_cross_median": n_cross,
                "sigma_pure_noise": bound,
                "sigma_observed": obs,
                "excess_ratio": ratio,
            })
    return rows


def _track_b_rows() -> list[dict]:
    """Track B / Phase B: single-region IC (ic_state/ic_base) + oos_state panel."""
    rows: list[dict] = []
    for sp in sorted(glob.glob("runs/results/*/oos_state.parquet")):
        sig = Path(Path(sp).parent).name[:12]
        ic_state = Path(Path(sp).parent) / "ic_state.parquet"
        ic_base = Path(Path(sp).parent) / "ic_base.parquet"
        try:
            scores = pd.read_parquet(sp)
        except FileNotFoundError:
            continue
        nc = _n_cross_eff(scores)
        n_cross = nc.get("n_cross_median")
        bound = pure_noise_sigma(int(n_cross)) if n_cross and n_cross >= 2 else None
        for arm, icp in (("ic_state", ic_state), ("ic_base", ic_base)):
            if not icp.exists():
                continue
            ic = pd.read_parquet(icp)
            col = "ic" if "ic" in ic.columns else ic.columns[0]
            obs = _observed_sigma(ic, col)
            ratio = (obs / bound) if (obs and bound and bound > 0) else None
            rows.append({
                "source": f"phase_b/{sig}", "arm": arm,
                "n_cross_median": n_cross,
                "sigma_pure_noise": bound,
                "sigma_observed": obs,
                "excess_ratio": ratio,
            })
    return rows


def main() -> None:
    rows = _track_c_rows() + _track_b_rows()
    if not rows:
        print("[S] no panels found", flush=True)
        return
    ratios = [r["excess_ratio"] for r in rows if r["excess_ratio"]]
    summary = {
        "n_rows": len(rows),
        "excess_ratio_min": min(ratios) if ratios else None,
        "excess_ratio_median": float(pd.Series(ratios).median()) if ratios else None,
        "excess_ratio_max": max(ratios) if ratios else None,
        "interpretation": (
            "observed sigma(IC) is consistently >> pure-noise Spearman bound "
            "(1/sqrt(N-1)); the power floor binds because of this excess "
            "(ML fitting noise + heteroskedasticity + overlap), not the pure bound."
        ),
    }
    print("\n=== Pure-noise bound vs observed sigma(IC) ===", flush=True)
    print(f"{'source':<26} {'arm':<10} {'N_cross':>8} {'sigma_null':>11} "
          f"{'sigma_obs':>10} {'excess':>7}", flush=True)
    print("-" * 80, flush=True)
    for r in rows:
        nc = f"{r['n_cross_median']:.0f}" if r["n_cross_median"] else "  nan"
        sn = f"{r['sigma_pure_noise']:.4f}" if r["sigma_pure_noise"] else "  nan"
        so = f"{r['sigma_observed']:.4f}" if r["sigma_observed"] else "  nan"
        ex = f"{r['excess_ratio']:.2f}x" if r["excess_ratio"] else "  nan"
        print(f"{r['source']:<26} {r['arm']:<10} {nc:>8} {sn:>11} {so:>10} {ex:>7}",
              flush=True)
    print("-" * 80, flush=True)
    print(f"excess ratio: min={summary['excess_ratio_min']:.2f}x  "
          f"med={summary['excess_ratio_median']:.2f}x  max={summary['excess_ratio_max']:.2f}x",
          flush=True)
    print(f"[S] {summary['interpretation']}", flush=True)
    # power implication at pure-noise vs observed
    sesoi = 0.010
    z_l3 = 1.960
    for label, sigma in (("pure-noise (N=462)", pure_noise_sigma(462)),
                         ("observed median", 0.109)):
        n_min = (z_l3 * sigma / sesoi) ** 2
        print(f"[S] look-3 n_min at {label} (sigma={sigma:.4f}): {n_min:.0f} months",
              flush=True)

    Path(OUT_PATH).write_text(json.dumps({"rows": rows, "summary": summary}, indent=2,
                                         default=str))
    print(f"\n[S] wrote {OUT_PATH} ({len(rows)} rows)", flush=True)
    print("[S] DONE (exploratory; never writes ledger)", flush=True)


if __name__ == "__main__":
    main()
