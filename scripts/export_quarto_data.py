"""Export aggregated research results to tracked JSON for the Quarto site.

Quarto renders on CI (GitHub Actions) where the gitignored runs/*.parquet and
runs/*.json artifacts are NOT available. This script reads those local artifacts
and writes small aggregated JSON files into quarto-site/data/ (TRACKED), so the
Quarto Python cells can read tracked data at render time. Re-run whenever results
change (the data/ files are committed).

Reuses pandas/json stdlib; no hand-rolled HTML. Writes ONLY to quarto-site/data/;
never touches runs/ledger.jsonl or frozen surfaces.

Usage::
    uv run python scripts/export_quarto_data.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

OUT = Path("quarto-site/data")
OUT.mkdir(parents=True, exist_ok=True)


def _stamp(payload: dict) -> dict:
    """Inject ISO-UTC snapshot timestamp (PIT honesty — every panel shows as-of)."""
    payload["snapshot_ts"] = datetime.now(timezone.utc).isoformat()
    return payload


def _load_json(path: str) -> dict | list:
    return json.loads(Path(path).read_text())


def export_sigma_survey() -> None:
    """sigma(IC) survey: observed vs pure-noise bound, per series."""
    survey = _load_json("runs/ic_noise_floor_survey.json")
    bound = _load_json("runs/ic_pure_noise_bound.json")
    # join on (source, arm); prefer the pure-noise rows that have both sigma values
    by_key = {}
    for r in survey.get("rows", []):
        if r.get("std") is not None:
            by_key[(r["source"], r["arm"])] = {"source": r["source"], "arm": r["arm"],
                                                "sigma_observed": r["std"]}
    for r in bound.get("rows", []):
        k = (r["source"], r["arm"])
        if k in by_key and r.get("sigma_pure_noise") and r.get("excess_ratio"):
            by_key[k].update({"n_cross": r["n_cross_median"],
                              "sigma_pure_noise": r["sigma_pure_noise"],
                              "excess_ratio": r["excess_ratio"]})
    rows = [v for v in by_key.values() if "sigma_pure_noise" in v]
    payload = {
        "rows": rows,
        "summary": {
            "excess_min": min(r["excess_ratio"] for r in rows),
            "excess_median": float(pd.Series([r["excess_ratio"] for r in rows]).median()),
            "excess_max": max(r["excess_ratio"] for r in rows),
            "n_series": len(rows),
        },
    }
    (OUT / "sigma_survey.json").write_text(json.dumps(_stamp(payload), indent=2, default=str))


def export_bps_sweep() -> None:
    """bps cost sensitivity: net/gross Sharpe vs bps."""
    df = pd.read_parquet("runs/track_b_net_cost_sweep.parquet")
    rows = [{"bps": float(r.bps), "net_sharpe": float(r.net_sharpe),
             "gross_sharpe": float(r.gross_sharpe),
             "avg_turnover": float(r.avg_turnover)}
            for r in df.itertuples()]
    (OUT / "bps_sweep.json").write_text(json.dumps(rows, indent=2))


def export_power_floor() -> None:
    """Power-floor n_min table + sigma context."""
    payload = {
        "sesoi": 0.010,
        "looks": [
            {"look": 1, "n": 60, "z": 2.772, "n_min_months": 869, "n_min_years": 72.5,
             "rci_level_pct": 99.44},
            {"look": 2, "n": 90, "z": 2.263, "n_min_months": 580, "n_min_years": 48.3,
             "rci_level_pct": 97.64},
            {"look": 3, "n": 120, "z": 1.960, "n_min_months": 435, "n_min_years": 36.2,
             "rci_level_pct": 95.00},
        ],
        "sigma_observed_median": 0.109,
        "sigma_pure_noise_n462": 0.0466,
        "n_min_at_pure_noise_look3_months": 83,
        "n_min_at_observed_look3_months": 456,
        "verdict": ("power floor binds via ML noise excess (2.0-4.4x pure-noise bound), "
                    "not the pure 1/sqrt(N-1) bound"),
    }
    (OUT / "power_floor.json").write_text(json.dumps(_stamp(payload), indent=2))


def export_evidence() -> None:
    """The 15-row evidence table (null results)."""
    cols = ["n", "result", "estimate", "ci_lo", "ci_hi", "p", "n_months", "grade"]
    data = [
        (1, "Phase B differential", -0.0008, -0.0106, 0.0090, 0.87, 125, "CV-proxy"),
        (2, "Phase C differential", -0.0065, -0.0195, 0.0066, 0.36, 125, "CV-proxy"),
        (3, "Phase D differential", -0.0030, -0.0137, 0.0078, 0.60, 125, "CV-proxy"),
        (4, "Phase E1 differential", -0.0028, -0.0115, 0.0059, 0.53, 125, "CV-proxy"),
        (5, "Track B treatment", 0.0055, -0.021, 0.033, 0.69, 125, "chron./explor."),
        (6, "Track B differential", 0.0076, -0.004, 0.020, 0.22, 125, "chron./explor."),
        (7, "Track C joint combined IC", -0.0070, -0.030, 0.016, 0.55, 71, "chron./explor."),
        (8, "Track C conditional-IC beta", -0.015, None, None, 0.20, 71, "explor."),
        (9, "Track C 3-layer cond.-IC", -0.0148, None, None, 0.21, 71, "explor."),
        (10, "Baseline-FF5", 0.0106, None, None, None, 125, "CV-proxy"),
        (11, "Baseline-RANK", 0.0154, None, None, 0.04, 125, "CV-proxy"),
        (13, "Track C asymmetric-35", -0.0121, -0.035, 0.011, 0.31, 71, "explor."),
        (14, "Track C asymmetric-41", -0.0088, -0.034, 0.016, 0.48, 71, "explor."),
        (15, "Track C confirmatory (climax)", -0.0088, -0.034, 0.016, 0.48, 71, "CONFIRMATORY"),
    ]
    rows = [dict(zip(cols, row, strict=True)) for row in data]
    (OUT / "evidence.json").write_text(json.dumps(rows, indent=2))


def export_ic_monthly() -> None:
    """Per-month confirmatory IC series (US / CN / combined) — the time-series view.

    The 71-month IC series is the densest tracked series; rendering it gives the
    site a real "data" view beyond the 15-row evidence snapshot, and the JSON stays
    tiny (66-71 rows × 4 cols).
    """
    df = pd.read_parquet("runs/track_c_confirmatory_ic_series.parquet")
    df.index = pd.to_datetime(df.index).strftime("%Y-%m")
    # Coalesce by month: the source can carry both a US-only and a CN-only row
    # for the same calendar month (when only one region had a fold that month).
    # Emitting both would produce duplicate month keys — a consumer plotting by
    # `month` would get double points / broken joins. Group by month and take
    # the first non-null value per region column, then re-sort ascending.
    def _first_non_null(s: pd.Series) -> float | None:
        s = s.dropna()
        return float(s.iloc[0]) if not s.empty else None

    grouped = df.groupby(level=0, sort=True)
    rows = [
        {
            "month": str(idx),
            "us": _first_non_null(g["us"]),
            "cn": _first_non_null(g["cn"]),
            "combined": _first_non_null(g["combined"]),
        }
        for idx, g in grouped
    ]
    (OUT / "ic_monthly.json").write_text(json.dumps(rows, indent=2, allow_nan=False))


def main() -> None:
    export_sigma_survey()
    export_bps_sweep()
    export_power_floor()
    export_evidence()
    export_ic_monthly()
    written = sorted(p.name for p in OUT.glob("*.json"))
    print(f"[export] wrote {len(written)} files to {OUT}/: {written}", flush=True)


if __name__ == "__main__":
    main()
