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
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import export_quarto_data as eq  # reuse the shared payload builders

WEB = Path("web/src/data/aionis")
WEB.mkdir(parents=True, exist_ok=True)
# Redirect the shared builders' output dir to the terminal data folder.
eq.OUT = WEB


def _load_ticker_metadata() -> pd.DataFrame:
    """Load cached ticker→(name, sector) map (built by scripts/build_ticker_metadata.py).

    Returns an empty-frame fallback if the cache is missing (export must never
    block on metadata — picks render with empty name/sector instead).
    """
    fp = Path("data/cache/ticker_metadata.parquet")
    if not fp.exists():
        return pd.DataFrame(columns=["ticker", "region", "name", "sector"])
    return pd.read_parquet(fp)


def _enrich_with_metadata(df: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    """Left-join OOS scores with ticker metadata. Missing names ⇒ empty string."""
    if meta.empty:
        df = df.copy()
        df["name"] = ""
        df["sector"] = ""
        return df
    return df.merge(meta[["ticker", "name", "sector"]], on="ticker", how="left").fillna(
        {"name": "", "sector": ""}
    )


def _calibration_disclaimer(calibration: dict) -> str:
    """Honest null-aware disclosure, shown beside every prob_up readout."""
    regions = calibration.get("regions", {})
    parts = []
    for r, payload in regions.items():
        m = payload["meta"]  # CalibrationMeta dataclass
        br = m.base_rate
        spread = m.prob_max - m.prob_min
        parts.append(
            f"{r.upper()}: {m.n_pairs}-pair calibration, base rate "
            f"{br:.2f}, calibrated range [{m.prob_min:.2f}, "
            f"{m.prob_max:.2f}] (spread {spread:.2f})"
        )
    return (
        "Model-readout probabilities (NOT investment advice). Method: "
        f"{calibration.get('method', 'platt')} calibration on historical OOS "
        "(score, realized forward-return) pairs; latest month predicted "
        "out-of-sample. Research verdict (ledger #49): combined rank-IC "
        "−0.0088, NULL — model discrimination is weak; calibrated probabilities "
        "cluster near the base rate. "
        + " | ".join(parts)
    )


def export_picks() -> tuple[str, int]:
    """Stock-pick ranking, top long + bottom short PER REGION (each region's own latest).

    Each region's panels are PIT-aligned on their own calendar (US ends
    2026-06-30, CN ends 2026-08-03 in the current snapshot); selecting top-N
    globally would silently drop whichever region lags. Per-region selection
    surfaces both markets. Enriches each pick with display name + sector +
    calibrated ``prob_up``. Writes:
      - picks.json / shorts.json: enriched rank lists
      - picks_meta.json: calibration meta + honest-null disclaimer
    """
    from aionis.eval.score_calibration import calibrate_latest_month, meta_to_jsonable

    df = pd.read_parquet("runs/track_c_confirmatory_oos_scores.parquet")
    df["date"] = pd.to_datetime(df["date"])
    meta = _load_ticker_metadata()

    # Calibration on real OOS history (per-region latest, walk-forward=False).
    us_panel_path = Path("data/cache/track_b_panel.parquet")
    cn_panel_path = Path("data/cache/cn_price_panel.parquet")
    us_panel = pd.read_parquet(us_panel_path) if us_panel_path.exists() else pd.DataFrame()
    cn_panel = pd.read_parquet(cn_panel_path) if cn_panel_path.exists() else pd.DataFrame()
    calibration = calibrate_latest_month(df, us_panel, cn_panel)

    # Per-region prob_up lookup.
    prob_lookup: dict[tuple[str, str], float] = {}
    for r, payload in calibration["regions"].items():
        if "latest" not in payload:
            continue
        for _, row in payload["latest"].iterrows():
            prob_lookup[(r, row["ticker"])] = float(row["prob_up"])

    # Per-region picks: top 10 US + top 10 CN long; bottom 3 US + bottom 2 CN short.
    picks: list[dict] = []
    shorts: list[dict] = []
    rank_counter = 0
    short_rank = 0
    for region, payload in calibration["regions"].items():
        if "latest" not in payload:
            continue
        region_latest = pd.Timestamp(payload["latest_date"])
        region_df = df[(df["region"] == region) & (df["date"] == region_latest)].copy()
        if region_df.empty:
            continue
        region_df = _enrich_with_metadata(region_df, meta)
        # Rank-change baseline: previous month in this region's OOS.
        region_dates = sorted(df[df["region"] == region]["date"].unique())
        prev_idx = region_dates.index(region_latest) - 1
        rp = {}
        if prev_idx >= 0:
            prev_df = df[df["date"] == region_dates[prev_idx]].copy()
            prev_df["r"] = prev_df["score"].rank(ascending=False, method="first").astype(int)
            rp = dict(zip(prev_df["ticker"], prev_df["r"], strict=True))
        # Top 10 long per region.
        top = region_df.nlargest(10, "score")
        for _, r in top.iterrows():
            rank_counter += 1
            picks.append({
                "rank": rank_counter,
                "ticker": r["ticker"],
                "region": r["region"],
                "name": r["name"],  # NOT r.name (Series index collision)
                "sector": r["sector"],
                "score": round(float(r["score"]), 3),
                "prob_up": round(prob_lookup.get((r["region"], r["ticker"]), 0.5), 3),
                "rank_change": (rp.get(r["ticker"]) - rank_counter) if rp.get(r["ticker"]) else None,
            })
        # Bottom 3 US / 2 CN short per region.
        n_short = 3 if region == "us" else 2
        bot = region_df.nsmallest(n_short, "score")
        for _, r in bot.iterrows():
            short_rank += 1
            shorts.append({
                "rank": short_rank,
                "ticker": r["ticker"],
                "region": r["region"],
                "name": r["name"],
                "sector": r["sector"],
                "score": round(float(r["score"]), 3),
                "prob_up": round(prob_lookup.get((r["region"], r["ticker"]), 0.5), 3),
            })
    (WEB / "picks.json").write_text(json.dumps(picks, indent=2))
    (WEB / "shorts.json").write_text(json.dumps(shorts, indent=2))

    # Calibration meta + honest-null disclaimer (display layer disclosure).
    meta_payload = {
        "latest_date": calibration["latest_date"],
        "method": calibration["method"],
        "walk_forward": calibration["walk_forward"],
        "regions": {
            r: {
                "latest_date": p["latest_date"],
                "meta": meta_to_jsonable(p["meta"]),
            }
            for r, p in calibration["regions"].items()
        },
        "disclaimer": _calibration_disclaimer(calibration),
    }
    (WEB / "picks_meta.json").write_text(json.dumps(meta_payload, indent=2, default=str))

    return str(pd.Timestamp(calibration["latest_date"]).date), len(picks) + len(shorts)


def export_sector_breakdown() -> None:
    """Aggregate latest-month OOS scores by sector — relative-favor ranking.

    Per sector: stock count, mean model score, mean calibrated P(up).
    Sectors with fewer than 3 stocks are dropped (noisy). A-share rows have
    empty sector (the listing file lacks industry) so they fall into the
    "Unclassified" bucket — disclosed in the methodology string, not hidden.
    Output: ``sector_breakdown.json`` with top/bottom sectors + methodology.
    """
    from aionis.eval.score_calibration import calibrate_latest_month

    oos = pd.read_parquet("runs/track_c_confirmatory_oos_scores.parquet")
    meta = _load_ticker_metadata()
    if meta.empty:
        (WEB / "sector_breakdown.json").write_text(json.dumps({
            "status": "awaiting_fetch",
            "methodology": "Run scripts/build_ticker_metadata.py first.",
            "sectors": [],
        }, indent=2))
        return

    latest_dates = oos.groupby("region")["date"].max().to_dict()
    latest = oos[oos.apply(lambda r: r["date"] == latest_dates.get(r["region"]), axis=1)].copy()
    latest = _enrich_with_metadata(latest, meta)
    latest["sector"] = latest["sector"].replace("", "Unclassified").fillna("Unclassified")

    us_panel_path = Path("data/cache/track_b_panel.parquet")
    cn_panel_path = Path("data/cache/cn_price_panel.parquet")
    us_panel = pd.read_parquet(us_panel_path) if us_panel_path.exists() else pd.DataFrame()
    cn_panel = pd.read_parquet(cn_panel_path) if cn_panel_path.exists() else pd.DataFrame()
    calibration = calibrate_latest_month(oos, us_panel, cn_panel)
    prob_lookup: dict[tuple[str, str], float] = {}
    for r, payload in calibration["regions"].items():
        if "latest" not in payload:
            continue
        for _, row in payload["latest"].iterrows():
            prob_lookup[(r, row["ticker"])] = float(row["prob_up"])
    latest["prob_up"] = [
        prob_lookup.get((row.region, row.ticker), 0.5) for row in latest.itertuples()
    ]

    grouped = []
    for sector, sub in latest.groupby("sector"):
        if len(sub) < 3:
            continue
        grouped.append({
            "sector": str(sector),
            "n_stocks": int(len(sub)),
            "mean_score": round(float(sub["score"].mean()), 3),
            "mean_prob_up": round(float(sub["prob_up"].mean()), 3),
            "regions": sorted(sub["region"].unique().tolist()),
        })
    grouped.sort(key=lambda s: s["mean_score"], reverse=True)
    payload = {
        "status": "ok",
        "latest_dates": {r: str(pd.Timestamp(d).date()) for r, d in latest_dates.items()},
        "methodology": (
            "Sector aggregation of latest-month OOS model scores + calibrated "
            "P(up), per region's own latest PIT-aligned date (US and CN panels "
            "may end on different months). US sectors from EDGAR SIC (public "
            "domain, industry-level); A-share 'sectors' are exchange-board tiers "
            "(科创板/创业板/主板/北交所 — a real tier classification, not industry). "
            "Sectors with <3 stocks dropped. Display-only, NOT a research claim."
        ),
        "n_sectors": len(grouped),
        "top_favored": grouped[:8],
        "least_favored": grouped[-5:][::-1] if len(grouped) >= 5 else grouped[::-1],
        "all_sectors": grouped,
    }
    (WEB / "sector_breakdown.json").write_text(json.dumps(payload, indent=2, default=str))


def export_picks_backtest() -> None:
    """Track record: past N months' top picks vs their realized forward returns.

    This is the honest 'prediction vs reality' audit — the soul of the
    anti-leakage project. For each of the past 6 realized months per region,
    take the top-5 picks by score, join the realized forward_return_h, and
    report hit rate + mean return vs base rate. If the model is null (rank-IC
    −0.0088), top picks' realized returns should cluster around the base rate.

    Output: ``picks_backtest.json`` with per-month entries + summary stats.
    """
    oos = pd.read_parquet("runs/track_c_confirmatory_oos_scores.parquet")
    oos["date"] = pd.to_datetime(oos["date"])
    meta = _load_ticker_metadata()
    us_panel = pd.read_parquet(Path("data/cache/track_b_panel.parquet"))
    us_panel["date"] = pd.to_datetime(us_panel["date"])
    cn_panel = pd.read_parquet(Path("data/cache/cn_price_panel.parquet"))
    cn_panel["date"] = pd.to_datetime(cn_panel["date"])

    # Number of months to show in the track record (env-configurable; default 99
    # = effectively all available OOS history. The OOS panel has up to 68 months
    # 2021-2026; reduce via BACKTEST_MONTHS env if the UI gets too long.)
    N_MONTHS = int(os.environ.get("BACKTEST_MONTHS", "99"))
    TOP_N = 5
    months_payload: list[dict] = []
    all_top_returns: list[float] = []
    all_base_returns: list[float] = []
    n_hits = 0
    n_total_picks = 0

    for region, panel in (("us", us_panel), ("cn", cn_panel)):
        region_oos = oos[oos["region"] == region][["date", "ticker", "score"]].copy()
        fwd = panel[["date", "ticker", "forward_return_h"]].copy()
        merged = region_oos.merge(fwd, on=["date", "ticker"], how="inner")
        merged = merged.dropna(subset=["forward_return_h", "score"])
        months = sorted(merged["date"].unique())
        # Last N_MONTHS realized months (exclude the very latest if partial).
        recent_months = months[-(N_MONTHS):]
        for month_ts in recent_months:
            month_df = merged[merged["date"] == month_ts]
            if len(month_df) < TOP_N:
                continue
            top = month_df.nlargest(TOP_N, "score")
            top = _enrich_with_metadata(top, meta)
            base_rate_return = float(month_df["forward_return_h"].mean())
            top_mean_return = float(top["forward_return_h"].mean())
            picks_list = []
            for _, r in top.iterrows():
                ret = float(r["forward_return_h"])
                hit = ret > 0
                if hit:
                    n_hits += 1
                n_total_picks += 1
                all_top_returns.append(ret)
                picks_list.append({
                    "ticker": r["ticker"],
                    "name": r["name"],
                    "score": round(float(r["score"]), 3),
                    "realized_return": round(ret, 4),
                    "hit": hit,
                })
            all_base_returns.append(base_rate_return)
            months_payload.append({
                "month": str(pd.Timestamp(month_ts).date()),
                "region": region,
                "picks": picks_list,
                "top_mean_return": round(top_mean_return, 4),
                "base_mean_return": round(base_rate_return, 4),
                "excess": round(top_mean_return - base_rate_return, 4),
            })

    hit_rate = n_hits / n_total_picks if n_total_picks > 0 else 0.0
    avg_top = sum(all_top_returns) / len(all_top_returns) if all_top_returns else 0.0
    avg_base = sum(all_base_returns) / len(all_base_returns) if all_base_returns else 0.0
    payload = {
        "methodology": (
            f"Past {N_MONTHS} realized months per region, top-{TOP_N} picks by "
            "model score vs their actual forward_return_h (≈21-session forward "
            "return). Hit rate = fraction of top picks that actually went up. "
            "Excess = top-picks mean return − all-stocks mean return that month. "
            "If the model is NULL (rank-IC −0.0088), hit rate ≈ base rate and "
            "excess ≈ 0. This is the honest 'prediction vs reality' audit."
        ),
        "months": months_payload,
        "summary": {
            "n_months": len(months_payload),
            "n_picks": n_total_picks,
            "hit_rate": round(hit_rate, 4),
            "avg_top_return": round(avg_top, 4),
            "avg_base_return": round(avg_base, 4),
            "avg_excess": round(avg_top - avg_base, 4),
        },
    }
    (WEB / "picks_backtest.json").write_text(json.dumps(payload, indent=2, default=str))


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
        o["date"]: float(o["value"])
        for o in raw["observations"]
        if o.get("value") not in (None, ".", "")
    }
    # Resample to monthly mean (2016-01 → today), mirroring export_market_context,
    # so the TACO stress chart shows the full Trump-era arc (not just ~1yr daily).
    monthly: dict[str, list[float]] = {}
    for date_str, val in by_date.items():
        monthly.setdefault(date_str[:7], []).append(val)
    vix_series = [
        {"month": m, "vix": round(sum(v) / len(v), 2)}
        for m, v in sorted(monthly.items())
        if m >= "2016-01"
    ]
    events = [
        {"date": "2025-02-01", "label": "Canada/Mexico/China tariff hike", "type": "escalation"},
        {"date": "2025-04-02", "label": "Reciprocal tariffs announced (Liberation Day)", "type": "escalation"},
        {"date": "2025-04-09", "label": "Reciprocal tariffs suspended (TACO origin)", "type": "concession"},
        {"date": "2025-05-12", "label": "US-China Geneva truce (tariffs cut)", "type": "concession"},
        {"date": "2025-07-21", "label": "Multiple tariff deadlines delayed", "type": "concession"},
    ]
    payload = {
        "methodology": (
            "Illustrative: VIX (FRED ALFRED, permissive) monthly mean from 2016-01 → "
            "today as the market-stress proxy; the 2025 TACO events are shown against "
            "the full Trump-era stress history. Event table hand-curated from public "
            "news (FT, CNBC, ABC). Not an Aionis research claim — demonstrative."
        ),
        "vix_series": vix_series,
        "events": events,
        "climbdowns_count": sum(1 for e in events if e["type"] == "concession"),
        "escalations_count": sum(1 for e in events if e["type"] == "escalation"),
        "latest_vix": vix_series[-1]["vix"] if vix_series else None,
        "latest_date": vix_series[-1]["month"] if vix_series else None,
    }
    (WEB / "taco.json").write_text(json.dumps(payload, indent=2))


def _theme_mean_signals(df: pd.DataFrame, cols: list[str]) -> list[dict]:
    """Cross-sectional mean of each column at the latest date → [{name, value}]."""
    out = []
    for c in cols:
        if c in df.columns:
            val = df[c].dropna()
            out.append({"name": c, "value": round(float(val.mean()), 4) if len(val) else None})
    return out


def _theme_monthly_series(panel: pd.DataFrame, col: str, n_months: int) -> list[dict]:
    """Last n_months of cross-sectional mean of `col` → [{month, value}]."""
    if col not in panel.columns:
        return []
    p = panel[["date", col]].dropna().copy()
    p["month"] = p["date"].dt.to_period("M").astype(str)
    series = p.groupby("month")[col].mean().sort_index().tail(n_months)
    return [{"month": m, "value": round(float(v), 4)} for m, v in series.items()]


def export_themes() -> None:
    """Seven-theme signal overview — display-only, NOT a research claim.

    Surfaces the frozen seven-theme platform's feature engineering (Track B,
    ``docs/track-b-preregistration.md``) so it is visible in the terminal.
    Aggregates are cross-sectional means at the latest realized month from the
    shared PIT panel (+ the Track-C macro-regime composite + the bps net-cost
    sweep). No new model fit, no ledger, no frozen-surface touch.
    """
    panel_path = Path("data/cache/track_b_panel.parquet")
    if not panel_path.exists():
        payload = {
            "status": "awaiting_fetch",
            "methodology": (
                "Seven-theme signal overview (display-only). Awaiting the shared "
                "PIT panel — run the data fetchers. Not an Aionis research claim."
            ),
            "themes": [],
        }
        (WEB / "themes.json").write_text(json.dumps(payload, indent=2))
        return

    panel = pd.read_parquet(panel_path)
    panel["date"] = pd.to_datetime(panel["date"])
    as_of = panel["date"].max()
    latest = panel[panel["date"] == as_of]

    # ① Price/market
    price = {
        "key": "price",
        "status": "live",
        "headline": "21d momentum + 63d vol + 252d β (cross-sectional mean)",
        "signals": _theme_mean_signals(latest, ["momentum_21d", "volatility_63d", "beta_252d", "reversal_5d"]),
        "series": _theme_monthly_series(panel, "momentum_21d", 12),
    }
    # ② Macro (Track-C macro-regime composite from regime_macro.parquet)
    macro = {"key": "macro", "status": "live", "signals": [], "series": []}
    macro_path = Path("data/cache/regime_macro.parquet")
    if macro_path.exists():
        mr = pd.read_parquet(macro_path)
        mr["date"] = pd.to_datetime(mr["date"])
        if "macro_regime" in mr.columns and len(mr):
            macro["headline"] = "macro-regime composite z (VIX+credit+term+DFF surprise)"
            macro["signals"] = [{"name": "macro_regime", "value": round(float(mr["macro_regime"].iloc[-1]), 4)}]
            macro["series"] = [
                {"date": str(d.date()), "value": round(float(v), 3)}
                for d, v in mr.tail(60)[["date", "macro_regime"]].values.tolist()
            ]
    # ③ Fundamentals
    fundamentals = {
        "key": "fundamentals",
        "status": "live",
        "headline": "ROE / margin / revenue growth / leverage (cross-sectional mean)",
        "signals": _theme_mean_signals(latest, ["roe", "profit_margin", "revenue_growth_12m", "leverage"]),
        "series": _theme_monthly_series(panel, "roe", 12),
    }
    # ④ News sentiment — forward-only (no historical corpus; honest)
    news = {
        "key": "news_sentiment",
        "status": "forward_only",
        "headline": "LLM extraction pool ready; no permissive historical corpus",
        "signals": [],
        "series": [],
    }
    # ⑤ Risk — alphalens tearsheet adapter not built (honest)
    risk = {
        "key": "risk",
        "status": "needs_work",
        "headline": "alphalens tearsheet adapter pending (empyrical metrics available)",
        "signals": [],
        "series": [],
    }
    # ⑥ Net cost — partial; surface the bps sweep net Sharpe (already exported)
    net_cost = {"key": "net_cost", "status": "partial", "signals": [], "series": []}
    bps_path = WEB / "bps_sweep.json"
    if bps_path.exists():
        try:
            sweep = json.loads(bps_path.read_text())
            rows = sweep if isinstance(sweep, list) else sweep.get("rows", [])
            row5 = next((r for r in rows if int(r.get("bps", -1)) == 5), None)
            if row5:
                net_cost["headline"] = "net Sharpe at 5 bps (from the bps sweep)"
                net_cost["signals"] = [
                    {"name": "net_sharpe_bps5", "value": round(float(row5["net_sharpe"]), 4)},
                    {"name": "gross_sharpe", "value": round(float(row5["gross_sharpe"]), 4)},
                    {"name": "avg_turnover", "value": round(float(row5["avg_turnover"]), 4)},
                ]
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            pass
    # ⑦ Market structure — liquidity + factor exposure
    market_structure = {
        "key": "market_structure",
        "status": "live",
        "headline": "Amihud illiquidity + 252d β (cross-sectional mean)",
        "signals": _theme_mean_signals(latest, ["amihud_illiquidity_21d", "beta_252d"]),
        "series": _theme_monthly_series(panel, "amihud_illiquidity_21d", 12),
    }

    payload = {
        "status": "ok",
        "as_of_date": str(as_of.date()),
        "methodology": (
            "Seven-theme signal overview (display-only, NOT a research claim). "
            "Aggregates are cross-sectional means over the S&P 500 PIT panel at "
            "the latest realized month; the macro theme uses the Track-C macro-"
            "regime composite; net cost uses the bps sweep. Themes marked "
            "forward_only / needs_work / partial have no real historical signal "
            "yet — shown honestly, never mocked. Not the frozen Track-B verdict."
        ),
        "themes": [price, macro, fundamentals, news, risk, net_cost, market_structure],
    }
    (WEB / "themes.json").write_text(json.dumps(payload, indent=2, default=str))


def export_theme_signals() -> None:
    """Operationalize the seven themes: per signal → direction × strength × favored.

    Turns the abstract 'cross-sectional mean = 0.3' into an actionable read:
    each theme signal becomes a direction (bullish/bearish/neutral, from a
    documented polarity heuristic), a normalized strength, and the top-5 tickers
    most exposed to it (joined with display name + sector). Reads the frozen
    panel's latest cross-section — DISPLAY ONLY, does NOT recompute OOS scores or
    touch the model. Not a research claim and not a buy recommendation (for
    'bearish_high' signals, 'favored' = most-exposed, not a long).
    """
    from aionis.eval.theme_signals import (
        SIGNAL_POLARITY,
        summarize_theme,
        theme_summary_to_jsonable,
    )

    panel_path = Path("data/cache/track_b_panel.parquet")
    if not panel_path.exists():
        payload = {
            "status": "awaiting_fetch",
            "methodology": (
                "Theme-signal operationalization (display-only). Awaiting the shared "
                "PIT panel. Not a research claim."
            ),
            "signals": {},
            "groups": [],
        }
        (WEB / "theme_signals.json").write_text(json.dumps(payload, indent=2))
        return
    panel = pd.read_parquet(panel_path)
    panel["date"] = pd.to_datetime(panel["date"])
    latest = panel["date"].max()
    latest_panel = panel[panel["date"] == latest].copy()
    meta = _load_ticker_metadata()
    latest_panel = _enrich_with_metadata(latest_panel, meta)

    groups = {
        "price": [
            "momentum_21d", "momentum_42d", "volatility_21d", "volatility_63d",
            "turnover_21d", "amihud_illiquidity_21d",
        ],
        "fundamentals": [
            "roe", "profit_margin", "revenue_growth_12m", "leverage", "debt_to_equity",
        ],
        "market_structure": ["beta_252d"],
    }
    all_cols = [c for grp in groups.values() for c in grp if c in latest_panel.columns]
    summaries = summarize_theme(latest_panel, all_cols, top_n=5)
    # Direction is recomputed here from latest-vs-trailing-6mo trend (scale-
    # independent), overriding the module's per-snapshot heuristic which uses
    # absolute thresholds that are scale-dependent (e.g. daily volatility ~0.02
    # wrongly reads "bullish"). Trend × polarity gives a meaningful market read.
    monthly = panel.groupby(panel["date"].dt.to_period("M"))[all_cols].mean()
    signals_json: dict[str, dict] = {}
    for sig, s in summaries.items():
        j = theme_summary_to_jsonable(s)
        j["group"] = next((g for g, colls in groups.items() if sig in colls), "other")
        if sig in monthly.columns and len(monthly) >= 2:
            ser = monthly[sig].dropna()
            latest_mean = float(ser.iloc[-1])
            trail = ser.iloc[-7:-1].dropna()
            trailing_mean = float(trail.mean()) if len(trail) else latest_mean
            rel = (latest_mean - trailing_mean) / abs(trailing_mean) if trailing_mean else 0.0
            polarity = SIGNAL_POLARITY.get(sig, "neutral")
            if polarity == "neutral":
                direction = "neutral"
            elif rel > 0.03:
                direction = "bullish" if polarity == "bullish_high" else "bearish"
            elif rel < -0.03:
                direction = "bearish" if polarity == "bullish_high" else "bullish"
            else:
                direction = "neutral"
            j["direction"] = direction
            j["latest_mean"] = round(latest_mean, 4)
            j["trailing_mean"] = round(trailing_mean, 4)
        signals_json[sig] = j
    payload = {
        "status": "ok",
        "as_of_date": str(latest.date()),
        "groups": list(groups.keys()),
        "signals": signals_json,
        "methodology": (
            "Theme-signal operationalization (display-only, NOT a research claim). "
            "Direction from a documented polarity heuristic (e.g. momentum/ROE high = "
            "bullish; volatility/leverage high = bearish). Strength = |mean cross-"
            "sectional z-score| clipped to [0,3]. Favored = top-5 tickers by the raw "
            "signal at the latest realized month. For 'bearish_high' signals, favored "
            "= most-exposed, NOT a buy recommendation. Reads only the frozen panel's "
            "latest cross-section; the model and OOS scores are untouched."
        ),
    }
    (WEB / "theme_signals.json").write_text(json.dumps(payload, indent=2, default=str))


def export_model_health() -> None:
    """Model-drift + calibration health monitor (display-only, leakage-safe).

    Reads the frozen OOS scores + PIT panels (same realized-pairs contract as
    ``export_picks`` / ``score_calibration``) and writes a per-region drift
    summary (score-distribution PSI + rolling cross-sectional rank-IC) so the
    terminal can surface 'is the model drifting lately' honestly. NOT a research
    claim and NOT a retrain trigger (rerun-to-significance is forbidden).
    """
    from aionis.eval.model_drift import drift_summary

    oos_path = Path("runs/track_c_confirmatory_oos_scores.parquet")
    if not oos_path.exists():
        payload = {
            "status": "awaiting_fetch",
            "methodology": (
                "Leakage-safe model-drift monitor (display-only). Awaiting OOS "
                "scores — run the confirmatory pipeline. NOT a research claim."
            ),
            "regions": {},
        }
        (WEB / "model_health.json").write_text(json.dumps(payload, indent=2))
        return
    oos = pd.read_parquet(oos_path)
    oos["date"] = pd.to_datetime(oos["date"])
    us_panel_path = Path("data/cache/track_b_panel.parquet")
    cn_panel_path = Path("data/cache/cn_price_panel.parquet")
    us_panel = pd.read_parquet(us_panel_path) if us_panel_path.exists() else pd.DataFrame()
    cn_panel = pd.read_parquet(cn_panel_path) if cn_panel_path.exists() else pd.DataFrame()
    summary = drift_summary(oos, us_panel, cn_panel)
    summary["status"] = "ok"
    (WEB / "model_health.json").write_text(json.dumps(summary, indent=2, default=str))


def export_calibration_reliability() -> None:
    """Walk-forward calibration reliability series + pooled OOS reliability diagram.

    Display-only, leakage-safe. For each realized month T, refits the Platt
    calibration on all realized (score, forward-return) pairs STRICTLY before T
    and predicts T's tickers' P(up); T's realized outcome then scores the
    prediction (backward audit). Surfaces 'does the calibrated P(up) stay
    trustworthy as the sample grows' — the leakage-safe form of 'use the latest
    data to self-correct the calibration'. NOT a research claim; the frozen
    LightGBM learner is never touched (research verdict ledger #49: NULL).
    """
    from aionis.eval.score_calibration import calibrate_walk_forward

    oos_path = Path("runs/track_c_confirmatory_oos_scores.parquet")
    if not oos_path.exists():
        payload = {
            "status": "awaiting_fetch",
            "methodology": (
                "Walk-forward calibration reliability (display-only). Awaiting OOS "
                "scores — run the confirmatory pipeline. NOT a research claim."
            ),
            "regions": {},
        }
        (WEB / "calibration_reliability.json").write_text(json.dumps(payload, indent=2))
        return
    oos = pd.read_parquet(oos_path)
    oos["date"] = pd.to_datetime(oos["date"])
    us_panel_path = Path("data/cache/track_b_panel.parquet")
    cn_panel_path = Path("data/cache/cn_price_panel.parquet")
    us_panel = pd.read_parquet(us_panel_path) if us_panel_path.exists() else pd.DataFrame()
    cn_panel = pd.read_parquet(cn_panel_path) if cn_panel_path.exists() else pd.DataFrame()
    reliability = calibrate_walk_forward(oos, us_panel, cn_panel)
    reliability["status"] = "ok"
    reliability["methodology"] = (
        "Walk-forward calibration reliability (display-only, leakage-safe). For "
        "each realized OOS month T, the Platt calibration map is refit on all "
        "realized (score, forward-return) pairs STRICTLY before T, then T's "
        "tickers are predicted; T's own realized outcome scores the prediction "
        "(backward audit). Per-month OOS ECE shows whether the calibrated P(up) "
        "stays trustworthy as the realized sample grows; the pooled reliability "
        "diagram bins all walk-forward OOS predictions (mean predicted P vs "
        "empirical up-frequency). Only the 2-param display map is refit — the "
        "frozen LightGBM learner is NEVER touched, and no ledger / frozen surface "
        "/ research estimator is affected. NOT a research claim and NOT a path to "
        "positive rank-IC (research verdict ledger #49: combined rank-IC −0.0088, NULL)."
    )
    (WEB / "calibration_reliability.json").write_text(json.dumps(reliability, indent=2, default=str))


def export_cot() -> None:
    """CFTC COT positioning-pressure index (display-only, exploratory).

    Reads ``data/cache/cot_aggregate.parquet`` (gitignored; produced by
    ``scripts/cot_fetch.py``). Free, no-API, US-government public domain; weekly
    (filed Friday) and archived snapshots are NOT revised (cleanest PIT surface).
    """
    import statistics

    fp = Path("data/cache/cot_aggregate.parquet")
    if not fp.exists():
        payload = {
            "status": "awaiting_fetch",
            "methodology": (
                "CFTC Commitments of Traders (COT) net non-commercial positioning "
                "+ 52-week crowding z-score. Free, no-API, US-gov public domain. "
                "Bounded fetch pending — run scripts/cot_fetch.py."
            ),
            "markets": [],
            "composite": {},
            "composite_series": [],
            "latest_date": None,
        }
        (WEB / "cot.json").write_text(json.dumps(payload, indent=2))
        return

    df = pd.read_parquet(fp)
    markets: list[dict] = []
    latest_zs: list[float] = []
    for mkt, sub in df.sort_values("date").groupby("market"):
        sub = sub.dropna(subset=["zscore"])
        if sub.empty:
            continue
        last = sub.iloc[-1]
        markets.append({
            "name": str(mkt),
            "net": int(last["net"]),
            "z": round(float(last["zscore"]), 2),
            "long": int(last["long"]),
            "short": int(last["short"]),
        })
        latest_zs.append(float(last["zscore"]))

    markets.sort(key=lambda m: m["z"], reverse=True)
    mean_z = round(statistics.mean(latest_zs), 2) if latest_zs else 0.0
    crowding = round(statistics.mean(abs(z) for z in latest_zs), 2) if latest_zs else 0.0
    comp = df.dropna(subset=["zscore"]).groupby("date")["zscore"].mean().sort_index()
    composite_series = [
        {"date": str(d)[:10], "z": round(float(z), 2)} for d, z in comp.items()
    ]
    payload = {
        "status": "ok",
        "methodology": (
            "CFTC Commitments of Traders (COT) — net non-commercial (speculator) "
            "positioning (Long - Short contracts) per key futures market, with a "
            "trailing 52-week crowding z-score. z>0 = net-long more crowded than "
            "usual; z<0 = net-short crowded. Free, no-API, US-gov public domain, "
            "weekly (filed Friday, archived and NOT revised). Coverage starts 2016 "
            "(Trump Era). Display-only, not a research claim."
        ),
        "markets": markets,
        "composite": {"mean_z": mean_z, "crowding": crowding, "n": len(markets)},
        "composite_series": composite_series,
        "latest_date": str(df["date"].max())[:10],
    }
    (WEB / "cot.json").write_text(json.dumps(payload, indent=2, default=str))


def export_form4() -> None:
    """Form 4 insider transactions (SEC EDGAR, display-only, exploratory).

    Reads the bounded fetch aggregate (``data/cache/form4_aggregate.parquet``,
    gitignored) if present; else reports ``awaiting_fetch`` honestly (no mock).
    Real public-domain data; filed-date PIT; non-derivative buy(A)/sell(D) only.
    """
    from collections import Counter

    fp = Path("data/cache/form4_aggregate.parquet")
    if not fp.exists():
        payload = {
            "status": "awaiting_fetch",
            "methodology": (
                "Form 4 insider transactions (SEC EDGAR EFTS, filed-date PIT, public "
                "domain). Non-derivative buy (A) / sell (D) only. Bounded large-cap "
                "fetch pending — run scripts/form4_fetch.py."
            ),
            "recent": [],
            "buys": 0,
            "sells": 0,
            "n_filers": 0,
            "top_insiders": [],
            "window": "pending",
            "n_issuers": 0,
        }
        (WEB / "form4.json").write_text(json.dumps(payload, indent=2))
        return

    df = pd.read_parquet(fp).sort_values("transaction_date", ascending=False)
    rows = [
        {
            "filer": str(r.get("filer_name", "")),
            "ticker": str(r.get("issuer_ticker") or r.get("ticker", "")),
            "date": str(r["transaction_date"])[:10],
            "action": str(r["buy_or_sell"]),
            "shares": int(r["shares"]) if pd.notna(r.get("shares")) else None,
            "price": (
                round(float(r["price_per_share"]), 2)
                if pd.notna(r.get("price_per_share"))
                else None
            ),
        }
        for _, r in df.head(50).iterrows()
    ]
    buys = int((df["buy_or_sell"] == "buy").sum())
    sells = int((df["buy_or_sell"] == "sell").sum())
    filer_counts = Counter(df["filer_name"].dropna()).most_common(10)
    n_issuers = int(df["issuer_ticker"].nunique()) if "issuer_ticker" in df else 0
    w_start = df["transaction_date"].min()
    w_end = df["transaction_date"].max()
    # Yearly aggregation (buys vs sells per year).
    yearly = []
    for year, sub in df.groupby(df["transaction_date"].dt.year):
        yearly.append({
            "year": int(year),
            "buys": int((sub["buy_or_sell"] == "buy").sum()),
            "sells": int((sub["buy_or_sell"] == "sell").sum()),
        })
    yearly.sort(key=lambda x: x["year"])
    payload = {
        "status": "ok",
        "methodology": (
            "Form 4 insider transactions (SEC EDGAR EFTS, filed-date PIT, public "
            "domain). Non-derivative pure buy (A) / sell (D) only — exercises and "
            "options excluded. Window spans 2016→today (Trump Era). Display-only, "
            "exploratory, not a research claim."
        ),
        "recent": rows,
        "buys": buys,
        "sells": sells,
        "n_filers": int(df["filer_name"].nunique()),
        "top_insiders": [{"filer": filer, "count": count} for filer, count in filer_counts],
        "window": f"{w_start.strftime('%Y-%m')}..{w_end.strftime('%Y-%m')} ({len(df)} txns, {n_issuers} issuers)",
        "n_issuers": n_issuers,
        "yearly": yearly,
    }
    (WEB / "form4.json").write_text(json.dumps(payload, indent=2, default=str))


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
    yearly = [
        {"year": int(y), "filings": sum(1 for r in rows if r["date"][:4] == y)}
        for y in sorted({r["date"][:4] for r in rows})
    ]
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
        "yearly": yearly,
    }
    (WEB / "smart_money.json").write_text(json.dumps(payload, indent=2))


def export_reddit_meta() -> None:
    """Reddit retail-sentiment — live if a forward snapshot exists, else honest 'awaiting_fetch'.

    Reads ``data/cache/reddit_snapshots.parquet`` (append-only cumulative) +
    ``reddit_last_run.json`` (status sidecar) written by
    ``scripts/reddit_fetch.py``. The collector runs zero-credential Atom RSS
    (Reddit blocked unauth ``.json`` + new OAuth via the Responsible Builder
    Policy, 2026). Forward-collection only -> no PIT history -> exploratory,
    display-only, NEVER an Aionis research claim. Matches the cot/form4
    'read-cache-or-await' pattern (no mock data).
    """
    pq = Path("data/cache/reddit_snapshots.parquet")
    status_path = Path("data/cache/reddit_last_run.json")
    methodology = (
        "Reddit retail-sentiment (mention volume + FinBERT sentiment) from "
        "r/wallstreetbets, r/stocks, r/investing. Forward-collection only "
        "(Pushshift dead 2023; no permissive historical corpus) -> no PIT history "
        "-> exploratory, display-only, NOT an Aionis research claim. Zero-credential "
        "Atom RSS transport (Reddit blocked unauth .json + new OAuth via the "
        "Responsible Builder Policy, 2026); upvote score available only when PRAW "
        "creds are present. Ticker extraction: $TICKER cashtags (any case) + bare "
        "UPPERCASE tokens >=4 chars (WSB ticker convention; lowercase = English prose)."
    )
    # Stable schema: EVERY key is present in both the live and awaiting branches so
    # the web's resolveJsonModule type (inferred from this file) is stable and the
    # build never breaks on a status transition.
    subreddits = ["wallstreetbets", "stocks", "investing"]
    if not pq.exists():
        latest_snapshot_ts = None
        n_snapshots = 0
        picks: list[dict] = []
        transport = None
        score_available = False
        reddit_status = "awaiting_fetch"
    else:
        df = pd.read_parquet(pq)
        side = json.loads(status_path.read_text()) if status_path.exists() else {}
        latest_ts = str(df["snapshot_ts"].max())
        latest = df[df["snapshot_ts"] == latest_ts].sort_values("mentions", ascending=False)
        picks = [
            {
                "ticker": r["ticker"],
                "mentions": int(r["mentions"]),
                "sentiment": round(float(r["sentiment_mean"]), 3),
                "bull_ratio": None if pd.isna(r["bull_ratio"]) else round(float(r["bull_ratio"]), 3),
                "score_sum": int(r["score_sum"]),
            }
            for _, r in latest.head(15).iterrows()
        ]
        latest_snapshot_ts = latest_ts
        n_snapshots = int(df["snapshot_ts"].nunique())
        transport = side.get("transport")
        score_available = bool(side.get("score_available", False))
        reddit_status = "live"
    payload = {
        "status": reddit_status,
        "methodology": methodology,
        "collector": "src/aionis/ingest/reddit_sentiment.py + scripts/reddit_fetch.py",
        "mode": "exploratory · forward-collection only · no backfill",
        "clearance": "7-gate (docs/data-intake-rubric.md): license / PIT / no-revision / selection-bias / politeness",
        "subreddits": subreddits,
        "how_to_activate": "uv run python scripts/reddit_fetch.py (zero-credential; no API key needed)",
        "latest_snapshot_ts": latest_snapshot_ts,
        "n_snapshots": n_snapshots,
        "transport": transport,
        "score_available": score_available,
        "score_note": None if score_available else "upvote score needs PRAW (OAuth); RSS path records 0",
        "picks": picks,
    }
    (WEB / "reddit.json").write_text(json.dumps(payload, indent=2, default=str))


def export_market_context() -> None:
    """Market context since 川普元年 (2016) — VIX + equal-weight market index + events.

    Provides the 'Trump Era' narrative anchor the terminal lacks: a 2016→today
    view of market stress (VIX) and broad-market growth (equal-weight US index),
    with curated event markers (elections, tariff wars, COVID, TACO). Uses panel
    data already covering 2016+ (no new fetch). Display-only, not a research claim.
    """
    # --- VIX monthly (FRED ALFRED, permissive, 2016+) ---
    vix_raw = json.loads(Path("data/cache/alfred_VIXCLS.json").read_text())
    vix_by_date = {
        o["date"]: float(o["value"])
        for o in vix_raw["observations"]
        if o.get("value") not in (None, ".", "")
    }
    # Resample to monthly mean.
    vix_monthly: dict[str, float] = {}
    for date_str, val in vix_by_date.items():
        month = date_str[:7]
        vix_monthly.setdefault(month, []).append(val)
    vix_series = [
        {"month": m, "vix": round(sum(v) / len(v), 2)}
        for m, v in sorted(vix_monthly.items())
        if m >= "2016-01"
    ]

    # --- US equal-weight market index (from panel close prices, 2016+) ---
    us = pd.read_parquet(Path("data/cache/track_b_panel.parquet"))
    us["date"] = pd.to_datetime(us["date"])
    us = us[["date", "ticker", "close"]].dropna()
    # Month-end close per ticker.
    month_end = us.groupby([us["date"].dt.to_period("M"), "ticker"])["close"].last().reset_index()
    month_end["month"] = month_end["date"].astype(str)
    # Per-ticker monthly return, then equal-weight cross-sectional mean.
    pivoted = month_end.pivot(index="month", columns="ticker", values="close").sort_index()
    monthly_ret = pivoted.pct_change()
    ew_ret = monthly_ret.mean(axis=1).dropna()
    ew_ret = ew_ret[ew_ret.index >= "2016-02"]  # first return needs prior month
    # Cumulative index (2016-02 = 100).
    cum_index = (1 + ew_ret).cumprod() * 100
    market_series = [
        {"month": m, "ret": round(float(r), 4), "index": round(float(cum_index.loc[m]), 2)}
        for m, r in ew_ret.items()
    ]

    # --- Curated market events (publicly verifiable, 2016-2026) ---
    # The core structural axis of the US market since 2016 is the President
    # (tariffs/fiscal) ↔ Federal Reserve (rates/independence) tug-of-war — NOT
    # personal milestones (inaugurations/elections). The Fed hike/cut cycle drives
    # the dollar and all markets; presidential tariffs and interference with Fed
    # independence (e.g. Miran's 2025 Fed Board appointment) are policy shocks.
    # Event markers center on these three structural levers. All publicly verifiable.
    events = [
        {"date": "2018-03-22", "label": "US-China tariff war begins", "type": "trade", "region": "us"},
        {"date": "2020-03-23", "label": "COVID market bottom", "type": "crisis", "region": "global"},
        {"date": "2022-03-16", "label": "Fed liftoff (hike cycle begins from zero)", "type": "monetary", "region": "us"},
        {"date": "2023-07-26", "label": "Fed peak 5.25-5.50% (cycle top)", "type": "monetary", "region": "us"},
        {"date": "2024-09-18", "label": "Fed first cut 50bp (pivot)", "type": "monetary", "region": "us"},
        {"date": "2025-02-01", "label": "Canada/Mexico/China tariff hike", "type": "trade", "region": "us"},
        {"date": "2025-03-12", "label": "Miran confirmed CEA chair (Fed-rollback architect)", "type": "fed_pressure", "region": "us"},
        {"date": "2025-04-02", "label": "Reciprocal tariffs announced (Liberation Day)", "type": "trade", "region": "us"},
        {"date": "2025-04-09", "label": "Reciprocal tariffs suspended (TACO origin)", "type": "trade", "region": "us"},
        {"date": "2025-05-12", "label": "US-China Geneva truce", "type": "trade", "region": "us"},
        {"date": "2025-08-07", "label": "Trump nominates Miran to Fed Board (replacing Kugler)", "type": "fed_pressure", "region": "us"},
        {"date": "2025-09-16", "label": "Miran confirmed to Fed Board — independence concern", "type": "fed_pressure", "region": "us"},
        {"date": "2025-09-17", "label": "Fed cut to 4.00-4.25%", "type": "monetary", "region": "us"},
    ]

    # Market risk stats from the equal-weight monthly returns (display-only).
    from aionis.eval.portfolio_risk import (
        risk_summary_to_jsonable,
    )
    from aionis.eval.portfolio_risk import (
        summarize as risk_summarize,
    )
    _ew_returns = [m["ret"] for m in market_series if isinstance(m.get("ret"), (int, float))]
    risk_json = (
        risk_summary_to_jsonable(risk_summarize(_ew_returns, periods_per_year=12))
        if len(_ew_returns) >= 12
        else None
    )

    payload = {
        "methodology": (
            "Market context since 2016. The structural axis is the President "
            "(tariffs/fiscal) ↔ Federal Reserve (rates/independence) tug-of-war: "
            "the Fed hike/cut cycle drives the dollar and all markets; presidential "
            "tariffs and Fed-independence interference (e.g. Miran's 2025 Fed Board "
            "appointment) are policy shocks. VIX = monthly mean of FRED VIXCLS "
            "(permissive, US-gov public domain). US index = equal-weight cross-"
            "sectional mean of monthly returns across the Track B panel (~566 S&P "
            "500 PIT constituents), rebased to 100 at 2016-02. Events are publicly "
            "verifiable milestones on the three structural levers (Fed cycle / "
            "trade / Fed-independence), not personal ceremonies. Display-only."
        ),
        "start_label": "2016 → · President ↔ Fed",
        "vix_series": vix_series,
        "market_series": market_series,
        "risk": risk_json,
        "events": events,
        "n_months": len(market_series),
        "date_range": [market_series[0]["month"], market_series[-1]["month"]] if market_series else [],
    }
    (WEB / "market_context.json").write_text(json.dumps(payload, indent=2, default=str))


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
    export_sector_breakdown()
    export_picks_backtest()
    export_taco()
    export_pick_conviction()
    export_themes()
    export_theme_signals()
    export_model_health()
    export_calibration_reliability()
    export_cot()
    export_form4()
    export_market_context()
    export_smart_money()
    export_reddit_meta()
    written = sorted(p.name for p in WEB.glob("*.json"))
    print(f"[export-terminal] wrote {len(written)} files to {WEB}/: {written}", flush=True)


if __name__ == "__main__":
    main()
