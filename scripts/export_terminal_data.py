"""Export aggregated data for the Next.js fintech terminal (web/src/data/aionis/).

Writes tracked JSON payloads so the terminal renders at build time (CI) without
the gitignored runs/*.parquet. Reuses ``export_quarto_data`` for the shared
payloads (evidence / power_floor / ic_monthly / sigma_survey / bps_sweep), then
adds terminal-specific picks / shorts / metrics from the confirmatory OOS scores.

Re-run whenever results change (the data/ files are committed). Writes ONLY to
web/src/data/aionis/; never touches runs/ledger.jsonl or frozen surfaces.

Usage::

    uv run python scripts/export_terminal_data.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import export_quarto_data as eq  # reuse the shared payload builders

WEB = Path("web/src/data/aionis")
WEB.mkdir(parents=True, exist_ok=True)
# Redirect the shared builders' output dir to the terminal data folder.
eq.OUT = WEB


def export_picks() -> tuple[str, int]:
    """Stock-pick ranking: latest OOS month, top-20 long + bottom-5 short.

    Rank change compares against the previous month (positive = moved up).
    """
    df = pd.read_parquet("runs/track_c_confirmatory_oos_scores.parquet")
    dates = sorted(df["date"].unique())
    latest, prev = dates[-1], dates[-2]

    def ranks(d: object) -> dict[str, int]:
        g = df[df["date"] == d].copy()
        g["r"] = g["score"].rank(ascending=False, method="first").astype(int)
        return dict(zip(g["ticker"], g["r"]))

    rl, rp = ranks(latest), ranks(prev)
    top = df[df["date"] == latest].nlargest(20, "score")
    picks = [
        {
            "rank": i + 1,
            "ticker": r.ticker,
            "region": r.region,
            "score": round(float(r.score), 3),
            "rank_change": (rp.get(r.ticker) - (i + 1)) if rp.get(r.ticker) else None,
        }
        for i, (_, r) in enumerate(top.iterrows())
    ]
    (WEB / "picks.json").write_text(json.dumps(picks, indent=2))

    bot = df[df["date"] == latest].nsmallest(5, "score")
    shorts = [
        {
            "rank": i + 1,
            "ticker": r.ticker,
            "region": r.region,
            "score": round(float(r.score), 3),
        }
        for i, (_, r) in enumerate(bot.iterrows())
    ]
    (WEB / "shorts.json").write_text(json.dumps(shorts, indent=2))
    return str(latest)[:10], int(len(df[df["date"] == latest]))


def export_metrics(latest: str, n_total: int) -> None:
    """Headline KPI payload (matches ledger row #49, the confirmatory climax)."""
    payload = {
        "combined_ic": -0.0088,
        "p": 0.484,
        "n_months": 71,
        "ci_lo": -0.034,
        "ci_hi": 0.016,
        "verdict": "NULL",
        "jt_look1": "NOT_EQUIVALENT",
        "h6": "PASS",
        "sesoi": 0.010,
        "latest_month": latest,
        "n_picks_total": n_total,
    }
    (WEB / "metrics.json").write_text(json.dumps(payload, indent=2))


def main() -> None:
    # Shared payloads (reused from the Quarto exporter, redirected to web/).
    eq.export_sigma_survey()
    eq.export_bps_sweep()
    eq.export_power_floor()
    eq.export_evidence()
    eq.export_ic_monthly()
    # Terminal-specific.
    latest, n_total = export_picks()
    export_metrics(latest, n_total)
    written = sorted(p.name for p in WEB.glob("*.json"))
    print(f"[export-terminal] wrote {len(written)} files to {WEB}/: {written}", flush=True)


if __name__ == "__main__":
    main()
