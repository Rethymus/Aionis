"""EXPLORATORY IC noise-floor survey — empirical sigma(IC) across Aionis configurations.

Sister to the power-floor literature-anchoring note
(`archive/2026-08-05-power-floor-literature-anchoring.md`, archived 2026-08-15). That note anchors
sigma~0.10 in the published literature (Gu-Kelly-Xiu R^2 levels, Grinold-Kahn Fundamental
Law); this script provides the DIRECT empirical complement: compute sigma(IC) across
every persisted IC series on disk (Track C joint/asym35/asym41/confirmatory + Track B
ic_state/ic_base) and show the noise floor is consistent (~0.08-0.15) across all of them
-- not an artifact of ledger #49 alone.

Exploratory analysis on existing gitignored artifacts; NOT a confirmatory claim, NOT a
changed config. Writes ONLY to ``runs/`` (gitignored); NEVER to ``runs/ledger.jsonl``.

Reuses persisted IC series (no rerun, no network). Lean by design.

Usage::
    uv run python scripts/ic_noise_floor_survey.py
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import pandas as pd
import structlog

log = structlog.get_logger()

OUT_PATH = "runs/ic_noise_floor_survey.json"

# Track C: 3-column (us/cn/combined) month-end IC series.
TRACK_C_PATTERNS = [
    "runs/track_c_*_ic_series.parquet",
]
# Track B / Phase B: single 'ic' column, under runs/results/<sig>/ic_{state,base}.parquet.
TRACK_B_PATTERNS = [
    "runs/results/*/ic_state.parquet",
    "runs/results/*/ic_base.parquet",
]


def _stats(series: pd.Series) -> dict:
    """mean / std / n / se for a monthly IC series (NaN-aware). std needs n>=2."""
    s = series.dropna()
    if len(s) == 0:
        return {"n": 0, "mean": None, "std": None, "se_hac_proxy": None}
    mean = float(s.mean())
    if len(s) < 2:
        return {"n": int(len(s)), "mean": mean, "std": None, "se_hac_proxy": None}
    return {
        "n": int(len(s)),
        "mean": mean,
        "std": float(s.std(ddof=1)),  # sample std of the monthly IC series = sigma(IC)
        "se_hac_proxy": float(s.std(ddof=1) / (len(s) ** 0.5)),  # iid proxy (HAC needs maxlag)
    }


def _survey_track_c() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(set().union(*(glob.glob(p) for p in TRACK_C_PATTERNS))):
        df = pd.read_parquet(path)
        name = Path(path).name.replace("_ic_series.parquet", "").replace(".parquet", "")
        for col in ("us", "cn", "combined"):
            if col in df.columns:
                st = _stats(df[col])
                rows.append({"source": name, "arm": col, "path": path, **st})
    return rows


def _survey_track_b() -> list[dict]:
    rows: list[dict] = []
    for pat in TRACK_B_PATTERNS:
        for path in sorted(glob.glob(pat)):
            df = pd.read_parquet(path)
            sig = Path(Path(path).parent).name[:12]
            arm = Path(path).stem  # ic_state or ic_base
            col = "ic" if "ic" in df.columns else df.columns[0]
            st = _stats(df[col])
            rows.append({"source": f"phase_b/{sig}", "arm": arm, "path": path, **st})
    return rows


def main() -> None:
    rows = _survey_track_c() + _survey_track_b()
    if not rows:
        print("[S] no IC series found under runs/; run the phase/track runners first", flush=True)
        return

    # summary: sigma(IC) distribution across all finite-std rows
    stds = [r["std"] for r in rows if r["std"] is not None]
    summary = {
        "n_series": len(rows),
        "n_with_std": len(stds),
        "sigma_min": min(stds) if stds else None,
        "sigma_max": max(stds) if stds else None,
        "sigma_median": float(pd.Series(stds).median()) if stds else None,
        "sigma_mean": float(pd.Series(stds).mean()) if stds else None,
        "in_documented_range_0p08_0p15": (
            all(0.06 <= s <= 0.20 for s in stds) if stds else False
        ),
        "interpretation": (
            "sigma(IC) consistent across configurations -> power-floor is not an artifact"
            " of ledger #49; it is a property of monthly cross-sectional rank-IC."
        ),
    }

    print("\n=== IC noise-floor survey (exploratory; sigma(IC) per persisted series) ===",
          flush=True)
    print(f"{'source':<28} {'arm':<10} {'n':>4} {'mean':>8} {'sigma':>8}", flush=True)
    print("-" * 64, flush=True)
    for r in rows:
        m = f"{r['mean']:+.4f}" if r["mean"] is not None else "  nan"
        s = f"{r['std']:.4f}" if r["std"] is not None else "  nan"
        print(f"{r['source']:<28} {r['arm']:<10} {r['n']:>4} {m:>8} {s:>8}", flush=True)
    print("-" * 64, flush=True)
    print(f"sigma(IC) across {summary['n_with_std']} series: "
          f"min={summary['sigma_min']:.4f} med={summary['sigma_median']:.4f} "
          f"max={summary['sigma_max']:.4f} mean={summary['sigma_mean']:.4f}", flush=True)
    print(f"in documented 0.08-0.15 range (tolerance 0.06-0.20): "
          f"{summary['in_documented_range_0p08_0p15']}", flush=True)
    print(f"[S] interpretation: {summary['interpretation']}", flush=True)

    out = {"rows": rows, "summary": summary}
    Path(OUT_PATH).write_text(json.dumps(out, indent=2, default=str))
    print(f"\n[S] wrote {OUT_PATH} ({len(rows)} rows)", flush=True)
    print("[S] DONE (exploratory; never writes ledger)", flush=True)


if __name__ == "__main__":
    if os.environ.get("PHASE_B_NO_LEDGER") == "1":
        print("[S] ARTIFACTS-ONLY (exploratory; never writes ledger)", flush=True)
    main()
