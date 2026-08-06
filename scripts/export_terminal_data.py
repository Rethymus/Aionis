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
        return dict(zip(g["ticker"], g["r"], strict=True))

    rp = ranks(prev)
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


def export_taco() -> None:
    """TACO pressure index — illustrative methodology, real data.

    VIX (FRED ALFRED, permissive) as the market-stress proxy; the event table is
    hand-curated from public news reports (labeled, not mock). NOT an Aionis
    research claim — methodology is demonstrative.
    """
    raw = json.loads(Path("data/cache/alfred_VIXCLS.json").read_text())
    by_date = {
        o["date"]: o["value"]
        for o in raw["observations"]
        if o.get("value") not in (None, ".", "")
    }
    recent = sorted(by_date)[-260:]
    vix_series = [{"date": d, "vix": float(by_date[d])} for d in recent]
    events = [
        {"date": "2025-02-01", "label": "Canada/Mexico/China tariff hike", "type": "escalation"},
        {"date": "2025-04-02", "label": "Reciprocal tariffs announced (Liberation Day)", "type": "escalation"},
        {"date": "2025-04-09", "label": "Reciprocal tariffs suspended (TACO origin)", "type": "concession"},
        {"date": "2025-05-12", "label": "US-China Geneva truce (tariffs cut)", "type": "concession"},
        {"date": "2025-07-21", "label": "Multiple tariff deadlines delayed", "type": "concession"},
    ]
    payload = {
        "methodology": (
            "Illustrative: VIX (FRED ALFRED, permissive) as the market-stress proxy; "
            "event table hand-curated from public news (FT, CNBC, ABC). Not an Aionis "
            "research claim — methodology demonstrative."
        ),
        "vix_series": vix_series,
        "events": events,
        "climbdowns_count": sum(1 for e in events if e["type"] == "concession"),
        "escalations_count": sum(1 for e in events if e["type"] == "escalation"),
        "latest_vix": vix_series[-1]["vix"] if vix_series else None,
        "latest_date": vix_series[-1]["date"] if vix_series else None,
    }
    (WEB / "taco.json").write_text(json.dumps(payload, indent=2))


def export_pick_conviction() -> None:
    """Pick-conviction index — cross-sectional dispersion of OOS model scores.

    Standard factor-research dispersion (std + top/bottom-decile spread; cf.
    Kelly-Pruitt-Su). High dispersion = the model finds clear winners; low =
    the market is hard to separate (a "low-conviction" regime). Aionis-unique
    model meta-signal. Illustrative methodology, not a research claim.
    """
    df = pd.read_parquet("runs/track_c_confirmatory_oos_scores.parquet")
    rows: list[dict] = []
    for date, sub in df.groupby("date"):
        s = sub["score"].dropna()
        if len(s) < 10:
            continue
        top = float(s.quantile(0.9))
        bot = float(s.quantile(0.1))
        rows.append({
            "date": str(date)[:10],
            "n": int(len(s)),
            "std": round(float(s.std()), 4),
            "decile_spread": round(top - bot, 4),
            "top_q": round(top, 3),
            "bot_q": round(bot, 3),
        })
    rows.sort(key=lambda r: r["date"])
    recent = rows[-12:]
    trailing_mean = sum(r["std"] for r in recent) / len(recent) if recent else None
    latest = rows[-1] if rows else None
    conviction = (
        "high" if latest and trailing_mean and latest["std"] > trailing_mean else "low"
    ) if latest else "unknown"
    payload = {
        "methodology": (
            "Cross-sectional dispersion of OOS model scores (std + top/bottom decile "
            "spread). High dispersion = model finds clear winners; low = market hard "
            "to separate. Standard factor-research dispersion. Aionis-unique model "
            "meta-signal; illustrative, not a research claim."
        ),
        "series": rows[-24:],
        "latest": latest,
        "conviction": conviction,
        "trailing_std_mean": round(trailing_mean, 4) if trailing_mean else None,
    }
    (WEB / "pick_conviction.json").write_text(json.dumps(payload, indent=2))


def export_smart_money() -> None:
    """Recent SC 13D institutional stake filings (SEC EDGAR EFTS, filed-date PIT).

    Aggregated from the cached per-filer full-text-search pulls. Real public-domain
    data (SEC), permissive. NOT a research claim — descriptive display of recent
    smart-money stake disclosures.
    """
    import glob
    import re

    rows: list[dict] = []
    for f in glob.glob("data/cache/efts_13d_*.json"):
        try:
            for item in json.loads(Path(f).read_text()):
                names = item.get("display_names") or []
                if len(names) < 2 or not item.get("file_date"):
                    continue
                # EDGAR 13D convention: display_names[0] = subject company (issuer/target);
                # display_names[1] = filer (reporting person / the smart-money entity).
                issuer = names[0]
                m = re.search(r"\(([A-Z]{1,6})\)", issuer)
                ticker = m.group(1) if m else ""
                target_clean = re.sub(r"\s*\(CIK.*$", "", issuer).strip()
                filer_clean = re.sub(r"\s*\(CIK.*$", "", names[1]).strip()
                form = item.get("form", "SC 13D")
                rows.append({
                    "filer": filer_clean,
                    "target": target_clean,
                    "ticker": ticker,
                    "date": item["file_date"],
                    "form": form,
                    "is_amendment": form.endswith("/A"),
                })
        except (json.JSONDecodeError, KeyError):
            continue
    rows.sort(key=lambda r: r["date"], reverse=True)
    recent = rows[:60]
    from collections import Counter
    active = Counter(r["filer"] for r in rows[:300]).most_common(10)
    payload = {
        "methodology": (
            "Recent SC 13D institutional stake filings (SEC EDGAR EFTS full-text "
            "search, filed-date point-in-time). Public domain, permissive. Real "
            "data; descriptive display, not an Aionis research claim."
        ),
        "recent_filings": recent,
        "active_filers": [{"filer": filer, "count": count} for filer, count in active],
        "total_filings": len(rows),
        "n_filers": len({r["filer"] for r in rows}),
        "latest_date": rows[0]["date"] if rows else None,
    }
    (WEB / "smart_money.json").write_text(json.dumps(payload, indent=2))


def export_reddit_meta() -> None:
    """Reddit retail-sentiment collector status — reported honestly.

    The forward collector (reddit_sentiment.py, PRAW + FinBERT, 7-gate cleared)
    exists but has never been activated, so no forward snapshot exists yet.
    """
    payload = {
        "status": "awaiting_activation",
        "collector": "src/aionis/ingest/reddit_sentiment.py (PRAW 8.0.2 BSD-2 + FinBERT Apache-2.0)",
        "mode": "exploratory · forward-collection only · no backfill (Pushshift dead)",
        "subreddits": ["wallstreetbets", "stocks", "investing"],
        "clearance": "7-gate (docs/data-intake-rubric.md): license / PIT / no-revision / selection-bias / politeness",
        "n_snapshots": 0,
        "picks": [],
    }
    (WEB / "reddit.json").write_text(json.dumps(payload, indent=2))


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
    export_taco()
    export_pick_conviction()
    export_smart_money()
    export_reddit_meta()
    written = sorted(p.name for p in WEB.glob("*.json"))
    print(f"[export-terminal] wrote {len(written)} files to {WEB}/: {written}", flush=True)


if __name__ == "__main__":
    main()
