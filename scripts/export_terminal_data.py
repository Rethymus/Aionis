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
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import export_quarto_data as eq  # reuse the shared payload builders

WEB = Path("web/src/data/aionis")
WEB.mkdir(parents=True, exist_ok=True)
# Redirect the shared builders' output dir to the terminal data folder.
eq.OUT = WEB


def _stamp(payload: dict) -> dict:
    """Inject an ISO-UTC snapshot timestamp (PIT honesty on the display layer).

    Owner directive: every terminal panel must show 'as of when' so a visitor
    can judge freshness. Mutates + returns the payload for chaining. Centralized
    so all export_* writers carry a consistent ``snapshot_ts`` without per-function
    drift.
    """
    payload["snapshot_ts"] = datetime.now(timezone.utc).isoformat()
    return payload


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


def _committed_json(name: str):
    """Parsed committed panel JSON (``web/src/data/aionis/<name>``), or None
    when absent/malformed — the retain-guard's view of the tracked value."""
    try:
        return json.loads((WEB / name).read_text(encoding="utf-8"))
    except Exception:
        return None


def _skip_retain(panel: str, reason: str) -> None:
    """Degenerate-output retain guard (macro_drivers precedent, generalized
    2026-08-22): a local run without the gitignored research caches (price
    panels, ticker metadata) must never clobber a live committed panel with an
    empty/partial shell — SKIP and keep the tracked JSON instead. Mirrors the
    cot/form4/ipo 'retain last-committed value' convention."""
    print(
        f"[export-terminal] SKIP {panel}: {reason} "
        "(tracked JSON retains last-committed value)",
        flush=True,
    )


def export_picks() -> tuple[str, int] | None:
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
            # Region-scoped prev frame: US and CN month-ends coincide ~70% of
            # the time (2026-05-29 etc.), so an unscoped date filter would rank
            # a mixed 1,400-row frame and shift rank_change by the other
            # region's whole universe.
            prev_df = df[
                (df["region"] == region) & (df["date"] == region_dates[prev_idx])
            ].copy()
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
    committed_picks = _committed_json("picks.json")
    if not picks and isinstance(committed_picks, list) and committed_picks:
        # Degenerate calibration (price-panel caches absent locally) — retain
        # the committed picks/shorts/meta trio. Returning None also makes
        # main() skip export_metrics(latest, n_total), keeping metrics.json
        # consistent with the retained picks instead of writing a degraded
        # hero payload built from an empty selection.
        _skip_retain("picks", "calibration produced no picks (price panels absent)")
        return None
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

    # Use .strftime (not .date) — `.date` is a bound method on Timestamp, so
    # str(...date) would serialize the repr "<bound method Timestamp.date ...>"
    # and leak a Python-internal string into the hero payload.
    return pd.Timestamp(calibration["latest_date"]).strftime("%Y-%m-%d"), len(picks) + len(shorts)


def export_sector_breakdown() -> None:
    """Aggregate latest-month OOS scores by sector — relative-favor ranking.

    Per sector: stock count, mean model score, mean calibrated P(up).
    Sectors with fewer than 3 stocks are dropped (noisy). A-share sectors
    are CSRC industry classification (证监会, via baostock — anonymous free
    API; 7-gate: docs/data-intake-baostock-industry.md), falling back to
    exchange-board tier where industry is missing — disclosed in the
    methodology string, not hidden.
    Output: ``sector_breakdown.json`` with top/bottom sectors + methodology.
    """
    from aionis.eval.score_calibration import calibrate_latest_month

    oos = pd.read_parquet("runs/track_c_confirmatory_oos_scores.parquet")
    meta = _load_ticker_metadata()
    if meta.empty:
        committed_sector = _committed_json("sector_breakdown.json")
        if committed_sector and committed_sector.get("status") == "ok":
            # Never clobber a live committed panel with the awaiting placeholder
            # (macro_drivers anti-pattern) — retain instead.
            _skip_retain(
                "sector_breakdown", "ticker metadata cache absent locally"
            )
            return
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
    committed_sector = _committed_json("sector_breakdown.json")
    committed_n = len(committed_sector.get("all_sectors", [])) if committed_sector else 0
    if committed_n and len(grouped) < committed_n // 2:
        # Partial metadata backfill (e.g. cn_industry cache half-rebuilt after
        # the 08-20 accident) collapses coverage — retain until the cache is
        # whole again rather than shipping a half-empty ranking.
        _skip_retain(
            "sector_breakdown",
            f"sector coverage collapsed ({len(grouped)} < 50% of committed {committed_n})",
        )
        return
    payload = {
        "status": "ok",
        "latest_dates": {r: str(pd.Timestamp(d).date()) for r, d in latest_dates.items()},
        "methodology": (
            "Sector aggregation of latest-month OOS model scores + calibrated "
            "P(up), per region's own latest PIT-aligned date (US and CN panels "
            "may end on different months). US sectors from EDGAR SIC (public "
            "domain, industry-level); A-share sectors are CSRC industry "
            "classification (证监会行业分类, via baostock — free anonymous API, "
            "BSD client; 7-gate: docs/data-intake-baostock-industry.md), "
            "falling back to exchange-board tier (科创板/创业板/主板/北交所) "
            "where industry is missing. Sectors with <3 stocks dropped. "
            "Display-only, NOT a research claim."
        ),
        "n_sectors": len(grouped),
        "top_favored": grouped[:8],
        "least_favored": grouped[-5:][::-1] if len(grouped) >= 5 else grouped[::-1],
        "all_sectors": grouped,
    }
    (WEB / "sector_breakdown.json").write_text(json.dumps(_stamp(payload), indent=2, default=str))


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
    (WEB / "picks_backtest.json").write_text(json.dumps(_stamp(payload), indent=2, default=str))


def _read_ledger_rows() -> list[tuple[int, dict]]:
    """Read runs/ledger.jsonl into (row_number, dict) pairs (READ-ONLY).

    Shared by the metrics + provenance + audit exports so the hero number's
    display source is the SAME ledger scan in every consumer — a single edit
    to the ledger propagates to all surfaces atomically, eliminating the
    "metrics.json desyncs from the ledger" structural gap. Returns [] if the
    ledger is absent (fresh CI checkout).
    """
    ledger_path = Path("runs/ledger.jsonl")
    if not ledger_path.exists():
        return []
    rows: list[tuple[int, dict]] = []
    for i, line in enumerate(ledger_path.read_text().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append((i, json.loads(line)))
        except json.JSONDecodeError:
            continue
    return rows


def _find_climax_row() -> tuple[int, dict] | None:
    """Find the confirmatory climax row (the headline claim's source).

    The ledger has multiple ``confirmatory:first`` rows (Phase B/C/D/E1 each
    have one for their own estimand), but only ONE is the headline Track C
    climax that carries the gated estimand: it has BOTH a nested
    ``combined_ic.mean`` dict (the rank-IC series result) AND a ``jt_gate``
    (the Jennison-Turnbull equivalence gate). The earlier-phase confirmatory
    rows lack both (different, non-gated estimands). Requiring both is an
    unfakeable discriminator — it cannot accidentally pick a Phase B row. We
    still scan (no hardcoded row number) so the function survives ledger
    growth. This is the single source of truth shared by export_metrics and
    export_headline_provenance.
    """
    for i, d in _read_ledger_rows():
        if d.get("event") == "confirmatory:first":
            cic = d.get("combined_ic")
            if isinstance(cic, dict) and "mean" in cic and "jt_gate" in d:
                return (i, d)
    return None


def export_metrics(latest: str, n_total: int) -> None:
    """Headline KPI payload — a LIVE projection of the confirmatory climax row.

    Previously this hardcoded the IC/p/CI literals (-0.0088, 0.484, ...), which
    left the hero number's display source structurally un-traced: a silent
    ledger edit would not propagate, and the two most prominent surfaces
    (VerdictAnchor + ResearchGlance) read this file with no ledger link. Now
    every field except latest_month/n_picks_total (display inputs) is derived
    from the SAME ledger scan as headline_provenance.json, and ledger_row +
    config_sig_short are emitted so every surface can trace the number to its
    frozen config. Falls back to the committed literals ONLY if the ledger is
    absent (fresh CI checkout without the gitignored ledger) so the terminal
    never renders empty.
    """
    def _num(v: object) -> float | None:
        return float(v) if isinstance(v, (int, float)) else None

    climax = _find_climax_row()
    if climax is not None:
        row_n, d = climax
        cic = d.get("combined_ic") or {}
        jt = d.get("jt_gate") or {}
        mean = cic.get("mean") if isinstance(cic, dict) else None
        ci_half = cic.get("ci_95_half") if isinstance(cic, dict) else None
        n_months = _num(d.get("n_months_ic") or (cic.get("n") if isinstance(cic, dict) else None))
        sig_full = d.get("config_sig") or ""
        payload = {
            "combined_ic": round(mean, 4) if isinstance(mean, (int, float)) else -0.0088,
            "p": round(_num(cic.get("p_hac")), 3) if isinstance(cic, dict) and isinstance(cic.get("p_hac"), (int, float)) else 0.484,
            "n_months": int(n_months) if n_months is not None else 71,
            "ci_lo": round(mean - ci_half, 4) if None not in (mean, ci_half) else -0.034,
            "ci_hi": round(mean + ci_half, 4) if None not in (mean, ci_half) else 0.016,
            "verdict": "NULL" if (isinstance(mean, (int, float)) and mean <= 0) else "NULL",
            "jt_look1": jt.get("look1_verdict", "NOT_EQUIVALENT"),
            "h6": "PASS" if d.get("H6_deterministic") else "FAIL",
            "sesoi": 0.010,
            "latest_month": latest,
            "n_picks_total": n_total,
            # The birth certificate inline: every surface that reads metrics
            # can now link the number to its frozen config without depending
            # on the sibling headline_provenance.json.
            "ledger_row": row_n,
            "config_sig_short": sig_full[:8] if sig_full else "",
        }
    else:
        # Ledger absent (fresh CI) — keep the terminal alive with the committed
        # literals. This branch is intentionally a fallback, not the main path.
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
    (WEB / "metrics.json").write_text(json.dumps(_stamp(payload), indent=2))


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
    (WEB / "taco.json").write_text(json.dumps(_stamp(payload), indent=2))


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


def _build_news_theme(cache_path: Path) -> dict:
    """Build the ``news_sentiment`` theme dict from the GDELT cache.

    Populates signals + a 24-month sparkline when the cache holds a real series;
    falls back to the honest "建设中" state when the cache is absent/malformed so
    ``_safe_export`` never degrades a tracked panel on a cold CI checkout. Pure
    (path in → dict out) so the wiring is hermetic-testable without the panel.
    """
    honest: dict = {
        "key": "news_sentiment",
        "status": "forward_only",
        "headline": "新闻情绪·建设中：GDELT 市场新闻语调（ECON_STOCKMARKET，2017-04 起）回填进行中，本快照暂无数据",
        "as_of": None,
        "signals": [],
        "series": [],
    }
    if not cache_path.exists():
        return honest
    try:
        gd = json.loads(cache_path.read_text())
        gseries = gd.get("series", [])
        tones = [r["tone"] for r in gseries if r.get("tone") is not None]
        if not (gseries and tones):
            return honest
        return {
            "key": "news_sentiment",
            "status": "live",
            "as_of": gseries[-1]["month"],  # latest GDELT month — PIT honesty
            "headline": (
                f"GDELT 通用语调（US 市场新闻，{gseries[0]['month']}→"
                f"{gseries[-1]['month']}）；通用词典非金融域——"
                "压力/情绪代理，非选股信号（display-only, exploratory）"
            ),
            "signals": [
                {"name": "tone_latest", "value": round(tones[-1], 3)},
                {"name": "tone_mean", "value": round(sum(tones) / len(tones), 3)},
                {"name": "tone_min", "value": round(min(tones), 3)},
                {"name": "volume_latest", "value": int(gseries[-1].get("volume", 0))},
                {"name": "n_months", "value": len(gseries)},
            ],
            # sparkline: last 24 months (full history is summarized in signals)
            "series": [{"month": r["month"], "value": r["tone"]} for r in gseries[-24:]],
        }
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return honest


def _refresh_news_sentiment_only(themes_path: Path, gdelt_cache_path: Path) -> str:
    """Panel-absent fallback: refresh ONLY news_sentiment in committed themes.json.

    news_sentiment is panel-independent (GDELT cache only), so it can update even
    when the shared PIT panel is absent (CI fresh checkout). Returns the refreshed
    news_sentiment status ('live' | 'forward_only'); returns '' if themes.json
    itself is absent (nothing to partially refresh). Pure (paths in) → hermetic-
    testable; never touches the panel-dependent themes.
    """
    if not themes_path.exists():
        return ""
    news = _build_news_theme(gdelt_cache_path)
    payload = json.loads(themes_path.read_text())
    payload["themes"] = [
        news if t.get("key") == "news_sentiment" else t
        for t in payload.get("themes", [])
    ]
    themes_path.write_text(json.dumps(_stamp(payload), indent=2, default=str))
    return news["status"]


def export_themes() -> None:
    """Seven-theme signal overview — display-only, NOT a research claim.

    Surfaces the frozen seven-theme platform's feature engineering (Track B,
    ``docs/track-b-preregistration.md``) so it is visible in the terminal.
    Aggregates are cross-sectional means at the latest realized month from the
    shared PIT panel (+ the Track-C macro-regime composite + the bps net-cost
    sweep). No new model fit, no ledger, no frozen-surface touch.
    """
    # Prefer the display panel (rebuilt daily in CI via track_b_materialize_panel
    # --display, prices through TODAY → fresh as_of); fall back to the frozen
    # research panel (track_b_panel.parquet) for local runs. Either is display-only
    # here — export_themes never touches aionis.eval.
    display_panel = Path("data/cache/display_panel.parquet")
    frozen_panel = Path("data/cache/track_b_panel.parquet")
    panel_path = display_panel if display_panel.exists() else frozen_panel
    if not panel_path.exists():
        # CI fresh checkout: BOTH panels absent. The panel-dependent themes
        # cannot rebuild — preserve their last-committed values. BUT
        # news_sentiment is panel-INDEPENDENT (GDELT cache only), so refresh it
        # in-place via the helper. Previously the early-return gated news_sentiment
        # behind the panel too — freezing it at 'forward_only' even after the GDELT
        # fetch succeeded (n=92/chunk). Root cause of '新闻情绪数据没有体现': the
        # fetch worked but the export never reached _build_news_theme.
        status = _refresh_news_sentiment_only(
            WEB / "themes.json", Path("data/cache/gdelt_news_sentiment.json")
        )
        if status:
            print(
                "[export-terminal] themes: panel absent — refreshed news_sentiment "
                f"only (status={status}); panel-dependent themes retain "
                "last-committed values",
                flush=True,
            )
        else:
            print(
                "[export-terminal] SKIP themes: panel absent and no committed "
                "themes.json to partially refresh",
                flush=True,
            )
        return

    panel = pd.read_parquet(panel_path)
    panel["date"] = pd.to_datetime(panel["date"])
    # Display-only close-only qlib factors (enrichment). Computed fresh in-memory;
    # the frozen panel parquet on disk is never touched → no research-pipeline /
    # leakage impact, no new phase. See docs/qlib-reuse-audit.md §1.
    if "close" in panel.columns:
        from aionis.features.qlib_close_factors import compute_qlib_close_factors

        panel = compute_qlib_close_factors(panel)
    as_of = panel["date"].max()
    latest = panel[panel["date"] == as_of]
    panel_as_of = str(as_of.date())  # per-theme PIT timestamp (honesty: show "data as of")

    # ① Price/market
    price = {
        "key": "price",
        "status": "live",
        "as_of": panel_as_of,
        "headline": "21d momentum + 63d vol + 252d β + 21d RSI(上行广度) + 63d timetohigh(距高点) (cross-sectional mean)",
        "signals": _theme_mean_signals(
            latest,
            ["momentum_21d", "volatility_63d", "beta_252d", "reversal_5d", "rsi_21d", "timetohigh_63d"],
        ),
        "series": _theme_monthly_series(panel, "momentum_21d", 12),
    }
    # ② Macro (Track-C macro-regime composite from regime_macro.parquet)
    macro = {"key": "macro", "status": "live", "as_of": None, "signals": [], "series": []}
    macro_path = Path("data/cache/regime_macro.parquet")
    if macro_path.exists():
        mr = pd.read_parquet(macro_path)
        mr["date"] = pd.to_datetime(mr["date"])
        if "macro_regime" in mr.columns and len(mr):
            macro["as_of"] = str(mr["date"].max().date())
            macro["headline"] = "macro-regime composite z (VIX+credit+term+DFF surprise)"
            macro["signals"] = [{"name": "macro_regime", "value": round(float(mr["macro_regime"].iloc[-1]), 4)}]
            macro["series"] = [
                {"date": str(d.date()), "value": round(float(v), 3)}
                for d, v in mr.tail(60)[["date", "macro_regime"]].values.tolist()
            ]
    if not macro["signals"]:
        # Honest-empty contract: a live theme MUST carry signals (the themes
        # contract test enforces >=1). regime_macro.parquet absent (e.g. the
        # build step failed or has not run yet) degrades the theme visibly
        # instead of exporting a "live" card with no data.
        macro["status"] = "needs_work"
        macro["headline"] = "macro-regime composite (regime_macro.parquet absent — awaiting build)"
    # ③ Fundamentals
    fundamentals = {
        "key": "fundamentals",
        "status": "live",
        "as_of": panel_as_of,
        "headline": "ROE / margin / revenue growth / leverage (cross-sectional mean)",
        "signals": _theme_mean_signals(latest, ["roe", "profit_margin", "revenue_growth_12m", "leverage"]),
        "series": _theme_monthly_series(panel, "roe", 12),
    }
    # ④ News sentiment — GDELT Doc 2.0 timelinetone (aggregate macro tone).
    # Display-only, exploratory. Pre-computed general-purpose lexicon tone over
    # US market news (theme:ECON_STOCKMARKET). Coverage 2017-04→today (Doc 2.0
    # debut). General lexicon, NOT finance-domain → regime/stress proxy, not a
    # stock pick. Pure builder → hermetic-testable without the panel.
    news = _build_news_theme(Path("data/cache/gdelt_news_sentiment.json"))
    # ⑤ Risk — cross-sectional risk factors (crash sensitivity + tail risk).
    # Distinct from the price theme's vol/β: downside β (down-market covariance),
    # idiosyncratic vol (stock-specific), return skew (left-tail), worst-day
    # drawdown. Computed from the panel's daily close prices. Lazy import — the
    # CI skip above returns before reaching here when the panel is absent.
    from aionis.features.risk_factors import compute_risk_factors

    risk_panel = compute_risk_factors(panel)
    risk_latest = risk_panel[risk_panel["date"] == as_of]
    risk = {
        "key": "risk",
        "status": "live",
        "as_of": panel_as_of,
        "headline": "下行β + 特质波动 + 偏度 + 最大单日回撤（横截面均值）",
        "signals": _theme_mean_signals(
            risk_latest,
            ["downside_beta", "idiosyncratic_volatility", "return_skewness", "worst_day_drawdown"],
        ),
        "series": _theme_monthly_series(risk_panel, "downside_beta", 12),
    }
    # ⑥ Net cost — partial; surface the bps sweep net Sharpe (already exported)
    net_cost = {"key": "net_cost", "status": "partial", "as_of": None, "signals": [], "series": []}
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
        "as_of": panel_as_of,
        "headline": "Amihud illiquidity + 252d β (cross-sectional mean)",
        "signals": _theme_mean_signals(latest, ["amihud_illiquidity_21d", "beta_252d"]),
        "series": _theme_monthly_series(panel, "amihud_illiquidity_21d", 12),
    }

    # Build the theme list first so we can summarize mixed freshness honestly.
    # The themes draw from independent sources (price/fundamentals from the
    # frozen PIT panel, macro from GDELT/ALFRED, net_cost from the bps sweep),
    # so their as_of dates legitimately differ. A single top-level as_of_date
    # that mirrors only the frozen panel would mislead a visitor into reading
    # the macro theme (genuinely fresher) as stale. Surface the full range.
    theme_list = [price, macro, fundamentals, news, risk, net_cost, market_structure]
    live_as_ofs = sorted(
        {t["as_of"] for t in theme_list if t.get("as_of")},
    )
    if len(live_as_ofs) <= 1:
        freshness = {"earliest": live_as_ofs[0] if live_as_ofs else None, "latest": live_as_ofs[0] if live_as_ofs else None, "mixed": False}
    else:
        freshness = {"earliest": live_as_ofs[0], "latest": live_as_ofs[-1], "mixed": True}

    payload = {
        "status": "ok",
        "as_of_date": str(as_of.date()),
        "freshness": freshness,
        "methodology": (
            "Seven-theme signal overview (display-only, NOT a research claim). "
            "Aggregates are cross-sectional means over the S&P 500 PIT panel at "
            "the latest realized month; the macro theme uses the Track-C macro-"
            "regime composite; net cost uses the bps sweep. Themes marked "
            "forward_only / needs_work / partial have no real historical signal "
            "yet — shown honestly, never mocked. Not the frozen Track-B verdict."
        ),
        "themes": theme_list,
    }
    (WEB / "themes.json").write_text(json.dumps(_stamp(payload), indent=2, default=str))


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

    # Prefer the DISPLAY panel (phase_b_fetch --display, prices through TODAY)
    # so the theme-signal direction/strength/favored reads refresh daily — the
    # frozen research panel (track_b_panel) stops at the 2026-06-30 cutoff and
    # would freeze the signals grid. Fall back to the frozen panel only when the
    # display panel is absent (fresh CI before the display-fetch step). The
    # feature columns are identical (same feature pipeline in materialize),
    # and this function computes display-only heuristics (no OOS scores).
    display_panel = Path("data/cache/display_panel.parquet")
    panel_path = display_panel if display_panel.exists() else Path("data/cache/track_b_panel.parquet")
    if not panel_path.exists():
        # CI fresh checkout: panel absent → preserve tracked JSON, don't overwrite.
        print(
            "[export-terminal] SKIP theme_signals: data/cache/track_b_panel.parquet "
            "not present (tracked JSON retains last-committed value)",
            flush=True,
        )
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
    (WEB / "theme_signals.json").write_text(json.dumps(_stamp(payload), indent=2, default=str))


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
    # Absent on a fresh CI checkout → let pd.read_parquet raise FileNotFoundError;
    # main()'s _safe_export guard then skips and preserves the tracked JSON
    # (refreshed locally when the confirmatory pipeline reruns). Do NOT overwrite
    # tracked real data with an empty awaiting payload on every CI run.
    oos = pd.read_parquet(oos_path)
    oos["date"] = pd.to_datetime(oos["date"])
    us_panel_path = Path("data/cache/track_b_panel.parquet")
    cn_panel_path = Path("data/cache/cn_price_panel.parquet")
    us_panel = pd.read_parquet(us_panel_path) if us_panel_path.exists() else pd.DataFrame()
    cn_panel = pd.read_parquet(cn_panel_path) if cn_panel_path.exists() else pd.DataFrame()
    summary = drift_summary(oos, us_panel, cn_panel)
    if not summary.get("regions"):
        committed_mh = _committed_json("model_health.json")
        if committed_mh and committed_mh.get("regions"):
            # Degenerate drift summary (price-panel caches absent locally) —
            # retain the committed per-region monitor.
            _skip_retain("model_health", "drift summary degenerate (price panels absent)")
            return
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
    # Absent on a fresh CI checkout → let pd.read_parquet raise FileNotFoundError;
    # main()'s _safe_export guard then skips and preserves the tracked JSON
    # (refreshed locally when the confirmatory pipeline reruns). Do NOT overwrite
    # tracked real data with an empty awaiting payload on every CI run.
    oos = pd.read_parquet(oos_path)
    oos["date"] = pd.to_datetime(oos["date"])
    us_panel_path = Path("data/cache/track_b_panel.parquet")
    cn_panel_path = Path("data/cache/cn_price_panel.parquet")
    us_panel = pd.read_parquet(us_panel_path) if us_panel_path.exists() else pd.DataFrame()
    cn_panel = pd.read_parquet(cn_panel_path) if cn_panel_path.exists() else pd.DataFrame()
    reliability = calibrate_walk_forward(oos, us_panel, cn_panel)
    if not reliability.get("regions"):
        committed_cr = _committed_json("calibration_reliability.json")
        if committed_cr and committed_cr.get("regions"):
            # Degenerate walk-forward (price-panel caches absent locally) —
            # retain the committed reliability series.
            _skip_retain("calibration_reliability", "walk-forward degenerate (price panels absent)")
            return
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
        # CI fresh checkout / fetch failed: preserve the tracked JSON, don't
        # overwrite real data with an empty awaiting payload.
        print(
            "[export-terminal] SKIP cot: data/cache/cot_aggregate.parquet not "
            "present (tracked JSON retains last-committed value)",
            flush=True,
        )
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
    (WEB / "cot.json").write_text(json.dumps(_stamp(payload), indent=2, default=str))


def export_form4() -> None:
    """Form 4 insider transactions (SEC EDGAR, display-only, exploratory).

    Reads the bounded fetch aggregate (``data/cache/form4_aggregate.parquet``,
    gitignored) if present; else reports ``awaiting_fetch`` honestly (no mock).
    Real public-domain data; filed-date PIT; non-derivative buy(A)/sell(D) only.
    """
    from collections import Counter

    fp = Path("data/cache/form4_aggregate.parquet")
    if not fp.exists():
        # CI fresh checkout / fetch failed: preserve the tracked JSON, don't
        # overwrite real data with an empty awaiting payload.
        print(
            "[export-terminal] SKIP form4: data/cache/form4_aggregate.parquet not "
            "present (tracked JSON retains last-committed value)",
            flush=True,
        )
        return

    df = pd.read_parquet(fp).sort_values("transaction_date", ascending=False)

    def _f4_doc_url(r: pd.Series) -> str:
        """EDGAR filing-index link per recent row (v1 disclosure pattern).

        Mirrors form_ipo's ``_filing_index_url``: ``/Archives/edgar/data/
        {cik}/{accession-nodash}/{accession}-index.htm`` — one stable link per
        filing, zero extra requests. The CIK used is the row's ``filer_cik``
        (the reporting owner — always an associated filer on their own Form 4,
        so the archive path resolves; cf. form8k which serves agent-prefixed
        accessions under the issuer CIK). Empty (never fabricated) when the
        aggregate predates the ``accession``/``filer_cik`` columns.
        """
        acc = r.get("accession")
        cik = r.get("filer_cik")
        if not isinstance(acc, str) or not acc or pd.isna(cik):
            return ""
        no_dash = acc.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{no_dash}/{acc}-index.htm"

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
            "doc_url": _f4_doc_url(r),
        }
        for _, r in df.head(200).iterrows()
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

    # Retain-merge (bounded-breadth pattern, smart_money precedent): a
    # ``--start``-bounded fetch covers only the recent window over a WIDER
    # issuer universe; the committed panel's pre-window history is retained
    # VERBATIM (monotonic — never dropped), and the universe widening is
    # disclosed in the methodology instead of silently changing history.
    methodology_note = ""
    committed = _committed_json("form4.json")
    c_window_start = None
    if (
        committed
        and committed.get("status") == "ok"
        and isinstance(committed.get("yearly"), list)
        and committed["yearly"]
        and yearly
    ):
        fresh_min_year = yearly[0]["year"]
        c_years = [y for y in committed["yearly"] if int(y["year"]) < fresh_min_year]
        if c_years:
            yearly = c_years + yearly
            buys = int(sum(y["buys"] for y in yearly))
            sells = int(sum(y["sells"] for y in yearly))
            c_window_start = str(committed.get("window", "")).split("..")[0]
            c_issuers = int(committed.get("n_issuers") or 0)
            if n_issuers > c_issuers:
                methodology_note = (
                    f" Universe widened from {c_issuers} to {n_issuers} issuers "
                    f"from {fresh_min_year} (bounded-breadth fetch; "
                    f"pre-{fresh_min_year} yearly aggregates retained verbatim "
                    "from the narrower universe)."
                )
            elif n_issuers < c_issuers:
                methodology_note = (
                    f" Universe narrowed from {c_issuers} to {n_issuers} issuers "
                    f"from {fresh_min_year} (pre-{fresh_min_year} yearly "
                    "aggregates retained verbatim from the wider universe)."
                )
            else:
                methodology_note = (
                    f" Universe unchanged at {n_issuers} issuers from "
                    f"{fresh_min_year} (pre-{fresh_min_year} yearly aggregates "
                    "retained verbatim)."
                )

    total_txns = buys + sells
    if c_window_start:
        window = (
            f"{c_window_start}..{w_end.strftime('%Y-%m')} "
            f"({total_txns} txns; {n_issuers} issuers current)"
        )
    else:
        window = f"{w_start.strftime('%Y-%m')}..{w_end.strftime('%Y-%m')} ({total_txns} txns, {n_issuers} issuers)"

    payload = {
        "status": "ok",
        "methodology": (
            "Form 4 insider transactions (SEC EDGAR EFTS, filed-date PIT, public "
            "domain). Non-derivative pure buy (A) / sell (D) only — exercises and "
            "options excluded. Window spans 2016→today (Trump Era). Recent rows "
            "link the EDGAR filing-index page (built from the row's accession + "
            "reporting-owner CIK — empty, never guessed, on pre-accession "
            "aggregates). Display-only, exploratory, not a research claim."
            + methodology_note
        ),
        "recent": rows,
        "buys": buys,
        "sells": sells,
        "n_filers": int(df["filer_name"].nunique()),
        "top_insiders": [{"filer": filer, "count": count} for filer, count in filer_counts],
        "window": window,
        "n_issuers": n_issuers,
        "yearly": yearly,
    }
    (WEB / "form4.json").write_text(json.dumps(_stamp(payload), indent=2, default=str))


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
    (WEB / "pick_conviction.json").write_text(json.dumps(_stamp(payload), indent=2))


_SM_FILER_PLACEHOLDER = "(申报人见原文)"  # daily index may not name the reporting person


def _sm_norm_name(s: str) -> str:
    """Uppercase + collapsed-whitespace company name (EFTS/daily name join key)."""
    import re

    return re.sub(r"\s+", " ", s.strip().upper())


def _sm_ticker_maps() -> tuple[dict[int, str], dict[str, str]]:
    """Offline CIK→ticker + normalized-name→ticker maps for 13D display rows.

    Built from EXISTING local caches only (no network): (1) the SEC
    ``company_tickers`` snapshot cached by ``aionis.ingest.cik_resolver``
    (``data/cache/cik_resolver_raw.json``, falling back to the parsed
    ``cik_resolver_tickers.json``); (2) the frozen EFTS 13D historical
    (``data/cache/efts_13d_*.json`` display_names carry as-of-filing tickers).
    A CIK with several tickers (share classes / preferreds) resolves to its
    first plain ticker in snapshot order — deterministic, common-stock-first.

    Display caveat (honest): the SEC snapshot is CURRENT, not as-of-filing —
    fine for a display label + stock-page link, never a research input.
    """
    import glob
    import re

    cik2tk: dict[int, str] = {}
    raw_fp = Path("data/cache/cik_resolver_raw.json")
    if raw_fp.exists():
        by_cik: dict[int, list[str]] = {}
        try:
            for v in json.loads(raw_fp.read_text()).values():
                if isinstance(v, dict) and v.get("cik_str") and v.get("ticker"):
                    by_cik.setdefault(int(v["cik_str"]), []).append(str(v["ticker"]))
        except (json.JSONDecodeError, AttributeError):
            by_cik = {}
    else:
        parsed_fp = Path("data/cache/cik_resolver_tickers.json")
        by_cik = {}
        if parsed_fp.exists():
            try:
                for tk, cik in json.loads(parsed_fp.read_text()).items():
                    by_cik.setdefault(int(cik), []).append(str(tk))
            except (json.JSONDecodeError, ValueError, AttributeError):
                by_cik = {}
    for cik, tks in by_cik.items():
        plain = [t for t in tks if "-" not in t]
        cik2tk[cik] = (plain or tks)[0]

    name2tk: dict[str, str] = {}
    for f in glob.glob("data/cache/efts_13d_*.json"):
        try:
            for item in json.loads(Path(f).read_text()):
                names = item.get("display_names") or []
                if len(names) >= 2 and item.get("file_date"):
                    m = re.search(r"\(([A-Z]{1,6})\)", names[0])
                    if m:
                        clean = re.sub(r"\s*\(CIK.*$", "", names[0]).strip()
                        name2tk.setdefault(_sm_norm_name(clean), m.group(1))
        except (json.JSONDecodeError, KeyError, AttributeError):
            continue
    return cik2tk, name2tk


def _sm_dedup_enrich(
    members: list[dict], cik2tk: dict[int, str], name2tk: dict[str, str]
) -> list[dict]:
    """One display row per 13D filing (accession), subject/filer resolved.

    The EDGAR daily crawler index lists a filing under EVERY covered company —
    the subject AND the filer entities with CIKs (e.g. accession
    0001213900-26-086686 appears under both ACRES Commercial Realty Corp.
    (subject) and ACRES Share Holdings, LLC (filer); the raw aggregate
    therefore double-lists ~40% of its rows and used to lose ticker + filer
    entirely). Resolution per accession group:

    - exactly ONE listed company (ticker resolvable) → it is the subject row
      (ticker filled); the other indexed names are its filers (joined " / ").
    - zero or multiple listed → keep EVERY member honestly (ticker where
      resolvable, placeholder filer): filings on unlisted targets (funds,
      LLCs, individuals) have no ticker at all, and a both-listed group
      (e.g. Gilead filing on Arcus) has no offline subject discriminator.
      Unresolved empties are counted in data_health ``source_health``.
    """
    def tk_of(m: dict) -> str:
        cik = m.get("target_cik")
        try:
            return cik2tk.get(int(cik), "") or name2tk.get(
                _sm_norm_name(str(m.get("target", ""))), ""
            )
        except (TypeError, ValueError):
            return name2tk.get(_sm_norm_name(str(m.get("target", ""))), "")

    def to_row(m: dict, ticker: str, filer: str) -> dict:
        return {
            "filer": filer,
            "target": str(m.get("target", "")).strip(),
            "ticker": ticker,
            "date": m["date"],
            "form": m.get("form", "SC 13D"),
            "is_amendment": bool(m.get("is_amendment")),
            "url": str(m.get("url", "")),
        }

    tk_members = [m for m in members if tk_of(m)]
    distinct = {tk_of(m) for m in tk_members}
    if len(distinct) == 1:
        subj = tk_members[0]
        others = [str(m.get("target", "")).strip() for m in members if m is not subj]
        return [to_row(subj, tk_of(subj), " / ".join(others[:2]) or _SM_FILER_PLACEHOLDER)]
    return [to_row(m, tk_of(m), _SM_FILER_PLACEHOLDER) for m in members]


def _rows_from_daily_aggregate(daily_path: Path) -> list[dict]:
    """Enriched, per-accession-deduped SC 13D rows from the daily aggregate.

    Shared by the full export and the retain-merge path so both produce
    identical row shapes and the same ticker/filer resolution.
    """
    try:
        raw = json.loads(daily_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(raw, list):
        return []
    cik2tk, name2tk = _sm_ticker_maps()
    groups: dict[str, list[dict]] = {}
    for r in raw:
        acc = str(r.get("accession", "")).removesuffix("-index.htm")
        if acc:
            groups.setdefault(acc, []).append(r)
    rows: list[dict] = []
    for members in groups.values():
        rows.extend(_sm_dedup_enrich(members, cik2tk, name2tk))
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def _sm_committed_extra(
    fresh_accessions: set[str],
    cik2tk: dict[int, str],
    name2tk: dict[str, str],
    committed_path: Path | None = None,
) -> tuple[list[dict], list[dict]]:
    """Committed recent rows the LOCAL daily aggregate does not cover.

    The daily cron may run on a checkout with a fuller ``sc13d_daily_aggregate``
    than the local ``data/cache`` (observed: committed JSON at 2026-08-17 while
    the local aggregate topped at 2026-08-07). Those committed rows are real
    filings — re-enrich them offline (CIK parsed from the row url's
    ``/data/{cik}/`` path, ticker re-resolved, deduped per accession) so a
    regen never regresses the panel's freshness or reverts to empty tickers.

    Returns ``(extra, verbatim)``: url-bearing rows re-enriched per accession
    vs url-less (EFTS-era) rows kept verbatim — the latter are only meaningful
    when the EFTS cache itself is absent, else the full path re-derives them.
    """
    import re

    source = committed_path or (WEB / "smart_money.json")
    try:
        prev = json.loads(source.read_text())
    except (json.JSONDecodeError, OSError):
        return [], []
    groups: dict[str, list[dict]] = {}
    verbatim: list[dict] = []
    for r in prev.get("recent_filings", []):
        url = str(r.get("url", ""))
        acc = url.rsplit("/", 1)[-1].removesuffix("-index.htm") if url else ""
        m = re.search(r"/data/(\d+)/", url)
        if not acc or m is None:
            if not url:
                verbatim.append(r)
            continue
        if acc in fresh_accessions:
            continue
        groups.setdefault(acc, []).append({
            "target": r.get("target", ""),
            "target_cik": int(m.group(1)),
            "date": r["date"],
            "form": r.get("form", "SC 13D"),
            "is_amendment": bool(r.get("is_amendment")),
            "accession": acc,
            "url": url,
        })
    extra: list[dict] = []
    for members in groups.values():
        extra.extend(_sm_dedup_enrich(members, cik2tk, name2tk))
    extra.sort(key=lambda r: r["date"], reverse=True)
    return extra, verbatim


def _refresh_smart_money_recent_only(committed_path: Path, daily_path: Path) -> dict | None:
    """Refresh smart_money's live window when only the daily index exists.

    The EFTS historical (2015→2024-12) is FINITE and closed (EFTS stopped
    indexing SC 13D; see aionis-edgar-efts-sc13d-frozen) and lives only in the
    committed JSON — regenerating it in CI would regress the 3754-filing set
    to a 25-CIK subset. Mirror :func:`_refresh_news_sentiment_only`: retain the
    committed historical aggregates (active_filers, pre-2025 yearly) and
    refresh only recent_filings, latest_date, and the post-cutoff (2025+)
    yearly counts, which come solely from the daily index (unioned with any
    committed rows the local aggregate does not cover — see
    :func:`_sm_committed_extra`).
    """
    if not committed_path.exists() or not daily_path.exists():
        return None
    try:
        prev = json.loads(committed_path.read_text())
    except json.JSONDecodeError:
        return None
    daily_rows = _rows_from_daily_aggregate(daily_path)
    if not daily_rows:
        return None
    try:
        fresh_accs = {
            str(r.get("accession", "")).removesuffix("-index.htm")
            for r in json.loads(daily_path.read_text())
        }
    except (json.JSONDecodeError, OSError):
        fresh_accs = set()
    cik2tk, name2tk = _sm_ticker_maps()
    extra, verbatim = _sm_committed_extra(fresh_accs, cik2tk, name2tk, committed_path)
    rows = daily_rows + extra + verbatim
    rows.sort(key=lambda r: r["date"], reverse=True)

    prev["recent_filings"] = rows[:120]
    prev["latest_date"] = max(
        str(prev.get("latest_date") or ""), str(rows[0]["date"])
    )

    by_year: dict[str, int] = {}
    for r in rows:
        by_year[r["date"][:4]] = by_year.get(r["date"][:4], 0) + 1
    yearly = [
        {**y, "filings": by_year.get(str(y["year"]), y["filings"])}
        if int(y["year"]) >= 2025
        else y
        for y in prev.get("yearly", [])
    ]
    for y in sorted(by_year):
        if not any(int(e["year"]) == int(y) for e in yearly):
            yearly.append({"year": int(y), "filings": by_year[y]})
    yearly.sort(key=lambda e: e["year"])
    prev["yearly"] = yearly
    prev["total_filings"] = sum(e["filings"] for e in yearly)

    prev = _stamp(prev)
    committed_path.write_text(json.dumps(prev, indent=2, ensure_ascii=False))
    return prev


def export_smart_money() -> None:
    """Recent SC 13D institutional stake filings (SEC EDGAR EFTS, filed-date PIT).

    Aggregated from the cached per-filer full-text-search pulls. Real public-domain
    data (SEC), permissive. NOT a research claim — descriptive display of recent
    smart-money stake disclosures.
    """
    import glob
    import re

    cache_files = glob.glob("data/cache/efts_13d_*.json")
    if not cache_files:
        # CI fresh checkout: the full 13D cache is gitignored (local-only), and
        # stakes_13d_fetch would produce only a 25-CIK SUBSET here that would
        # regress the committed 3754-filing set. Refresh ONLY the live window
        # (recent_filings / latest_date / post-cutoff yearly) from the daily
        # index and retain the committed historical aggregates — the EFTS
        # historical is a finite closed set (EFTS stopped indexing SC 13D after
        # 2024-12-17), so it never regrows and need not be re-pulled.
        if _refresh_smart_money_recent_only(
            WEB / "smart_money.json", Path("data/cache/sc13d_daily_aggregate.json")
        ) is not None:
            print(
                "[export-terminal] smart_money: EFTS historical absent — refreshed "
                "recent_filings/latest_date/post-2024 yearly from the daily index; "
                "committed historical aggregates retained",
                flush=True,
            )
        else:
            print(
                "[export-terminal] SKIP smart_money: no data/cache/efts_13d_*.json "
                "(tracked JSON retains last-committed value)",
                flush=True,
            )
        return
    rows: list[dict] = []
    for f in cache_files:
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
    # Merge recent SC 13D from the EDGAR daily crawler index — this unfreezes the
    # panel past the 2024-12-17 EFTS cutoff (see aionis-edgar-efts-sc13d-frozen).
    # The daily index lists a filing under EVERY covered company (subject AND
    # filer entities), so _rows_from_daily_aggregate dedups per accession,
    # resolves the subject (the listed company), backfills its ticker offline
    # (SEC snapshot CIK map + EFTS name map) and surfaces the co-indexed names
    # as the filer. Rows the LOCAL aggregate does not cover (a fresher cron
    # cache elsewhere) are unioned in re-enriched, so a regen never regresses.
    daily_path = Path("data/cache/sc13d_daily_aggregate.json")
    daily_rows: list[dict] = []
    if daily_path.exists():
        daily_rows = _rows_from_daily_aggregate(daily_path)
    if daily_rows:
        try:
            fresh_accs = {
                str(r.get("accession", "")).removesuffix("-index.htm")
                for r in json.loads(daily_path.read_text())
            }
        except (json.JSONDecodeError, OSError):
            fresh_accs = set()
        extra, _verbatim = _sm_committed_extra(
            fresh_accs, *_sm_ticker_maps()
        )
        rows.extend(daily_rows)
        rows.extend(extra)
    rows.sort(key=lambda r: r["date"], reverse=True)
    recent = rows[:120]
    from collections import Counter
    # Rank real filers: EFTS rows name the reporting person; daily-index rows
    # surface the co-indexed filer entities for single-subject accessions. The
    # sentinel placeholder (ambiguous / no offline discriminator) is excluded.
    active = Counter(
        r["filer"] for r in rows if r["filer"] and not r["filer"].startswith("(")
    ).most_common(10)
    yearly = [
        {"year": int(y), "filings": sum(1 for r in rows if r["date"][:4] == y)}
        for y in sorted({r["date"][:4] for r in rows})
    ]
    payload = {
        "methodology": (
            "Recent SC 13D institutional stake filings (SEC EDGAR, filed-date "
            "point-in-time). Public domain, permissive. Two sources: EFTS full-"
            "text search for 2015→2024-12 (filer + target + ticker), and the EDGAR "
            "daily crawler index for 2024-12→today. The daily index lists a "
            "filing under EVERY covered company (subject AND filer entities), "
            "so rows are deduped per accession: the listed company is the "
            "subject (ticker backfilled OFFLINE from the cached SEC "
            "company_tickers snapshot — current-snapshot display label, not "
            "as-of-filing — plus the frozen EFTS name map), and the co-indexed "
            "names surface as the filer. Filings on unlisted targets (funds, "
            "LLCs, individuals) or with several listed candidates honestly "
            "keep an empty ticker / placeholder filer (counted in "
            "data_health.source_health). Real data; descriptive display, not "
            "an Aionis research claim."
        ),
        "recent_filings": recent,
        "active_filers": [{"filer": filer, "count": count} for filer, count in active],
        "total_filings": len(rows),
        "n_filers": len({r["filer"] for r in rows}),
        "latest_date": rows[0]["date"] if rows else None,
        "yearly": yearly,
    }
    (WEB / "smart_money.json").write_text(json.dumps(_stamp(payload), indent=2))


def export_stakes13g() -> None:
    """SC 13G passive-stake filing stream — EDGAR daily index (display-only).

    Reads ``data/cache/sc13g_daily_aggregate.json`` (gitignored; produced by
    ``scripts/stakes13g_fetch.py`` over a trailing ~120-day window). EFTS froze
    on the Schedule 13 family after 2024-12-17 (live-verified 2026-08-22), so
    the daily crawler index is the source — it lists a filing under EVERY
    covered company, so rows are grouped per accession and resolved with the
    same offline heuristic as the 13D daily path (``_sm_dedup_enrich``): the
    one listed company is the subject, the co-indexed names surface as the
    filer; ambiguous groups keep every member honestly (placeholder filer).
    The % ownership / passive-state machine needs per-document parsing and is
    DEFERRED (disclosed, never fabricated) — each row is one immutable filing.
    """
    fp = Path("data/cache/sc13g_daily_aggregate.json")
    if not fp.exists():
        print(
            "[export-terminal] SKIP stakes_13g: data/cache/sc13g_daily_aggregate.json "
            "not present (tracked JSON retains last-committed value)",
            flush=True,
        )
        return
    try:
        raw = json.loads(fp.read_text())
    except (json.JSONDecodeError, OSError):
        print(
            "[export-terminal] SKIP stakes_13g: malformed sc13g_daily_aggregate.json "
            "(tracked JSON retains last-committed value)",
            flush=True,
        )
        return
    if not isinstance(raw, list):
        print(
            "[export-terminal] SKIP stakes_13g: unexpected aggregate shape "
            "(tracked JSON retains last-committed value)",
            flush=True,
        )
        return

    # Group per accession (the index lists subject AND filer entities), then
    # resolve subject/filer + offline ticker with the 13D daily-path heuristic.
    cik2tk, name2tk = _sm_ticker_maps()
    groups: dict[str, list[dict]] = {}
    for r in raw:
        acc = str(r.get("accession", ""))
        if acc:
            groups.setdefault(acc, []).append(r)
    rows: list[dict] = []
    for members in groups.values():
        rows.extend(_sm_dedup_enrich(members, cik2tk, name2tk))
    rows.sort(key=lambda r: r["date"], reverse=True)
    if not rows:
        print(
            "[export-terminal] SKIP stakes_13g: 0 filings in aggregate "
            "(tracked JSON retains last-committed value)",
            flush=True,
        )
        return

    by_form = {k: 0 for k in ("SC 13G", "SC 13G/A")}
    for r in rows:
        by_form[r["form"]] = by_form.get(r["form"], 0) + 1
    filings = []
    for r in rows[:150]:
        # Normalize the daily index's http:// links to https:// (EDGAR serves
        # both; https is the terminal's link convention).
        url = str(r["url"])
        if url.startswith("http://www.sec.gov/"):
            url = "https://www.sec.gov/" + url[len("http://www.sec.gov/"):]
        filings.append({
            "filer": str(r["filer"]),
            "target": str(r["target"]),
            "ticker": str(r["ticker"]) or None,  # unresolved → honest null
            "date": str(r["date"]),
            "form": str(r["form"]),
            "doc_url": url,
        })
    dates = [r["date"] for r in rows]
    payload = {
        "status": "ok",
        "as_of": max(dates),
        "window": {"start": min(dates), "end": max(dates)},
        "total": int(len(rows)),
        "by_form": {k: int(v) for k, v in by_form.items() if v},
        "filings": filings,
        "methodology": (
            "SC 13G passive-stake filing stream — SEC EDGAR daily crawler "
            "index (public domain, 17 U.S.C. §105), trailing ~120-day window, "
            "filed-date point-in-time; a SC 13G/A amendment is a new filing, "
            "never a silent overwrite. EFTS full-text search froze on the "
            "Schedule 13 family after 2024-12-17 (live-verified: forms=SC 13G "
            "returns 0 hits for 2025+ windows), so the daily index is the "
            "source. It lists a filing under EVERY covered company, so rows "
            "are DEDUPED per accession: the one listed company is the SUBJECT "
            "(ticker backfilled OFFLINE from the cached SEC company_tickers "
            "snapshot — a current-snapshot display label, not as-of-filing) "
            "and the co-indexed names surface as the FILER; ambiguous or "
            "unlisted groups honestly keep every member (placeholder filer / "
            "null ticker, counted in data_health.source_health), so the row "
            "count can slightly exceed the distinct-accession count. Honest "
            "v1 limits, disclosed not papered over: the % ownership, share "
            "count, event date, and the passive/active/exited state machine "
            "live INSIDE the filing documents and are NOT parsed here "
            "(per-accession index.json fetches would cost thousands of "
            "requests — deferred); each row links the filing's EDGAR index "
            "page, which lists every document and names the reporting "
            "person. Counts are FILING counts, not holder counts. "
            "Display-only, exploratory, not a research claim; NOT part of "
            "any OOS pipeline."
        ),
    }
    (WEB / "stakes_13g.json").write_text(json.dumps(_stamp(payload), indent=2))
    n_tk = sum(1 for f in filings if f["ticker"])
    print(
        f"[export-terminal] stakes_13g: {payload['total']} filings "
        f"{payload['by_form']}, as_of {payload['as_of']}, "
        f"ticker {n_tk}/{len(filings)} on top-{len(filings)}",
        flush=True,
    )


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
        # CI fresh checkout / fetch failed: preserve the tracked JSON (the last
        # accumulated snapshot), don't overwrite with an empty awaiting payload.
        print(
            "[export-terminal] SKIP reddit_meta: reddit snapshot cache not present "
            "(tracked JSON retains last-committed value)",
            flush=True,
        )
        return
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
        # Retail pressure (GME-style velocity × crowding-z × sentiment) from the
        # FULL snapshot history. Forward-only; needs ≥14 days to grade — the daily
        # cron accumulates. Empty/accumulating until then (honest, not broken).
        from aionis.eval.retail_pressure import compute_pressure, pressure_summary_to_jsonable
        hist = pd.DataFrame({
            "date": pd.to_datetime(df["snapshot_ts"]).dt.strftime("%Y-%m-%d"),
            "ticker": df["ticker"],
            "mentions": df["mentions"].astype(int),
            "sentiment": df["sentiment_mean"].astype(float),
        })
        pressure_latest = str(pd.to_datetime(df["snapshot_ts"]).max().date())
        try:
            pres = compute_pressure(hist, pressure_latest, lookback_days=30)
        except ValueError:
            pres = {}
        pressure = {
            "status": "ok" if pres else ("accumulating" if n_snapshots > 0 else "awaiting"),
            "by_ticker": {tk: pressure_summary_to_jsonable(p) for tk, p in pres.items()},
            "n_snapshots": n_snapshots,
            "latest_date": pressure_latest,
            "note": "GME-style retail pressure (mention velocity × crowding-z × sentiment). Needs ≥14 days of snapshots to grade; the daily cron accumulates.",
        }
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
        "pressure": pressure,
    }
    (WEB / "reddit.json").write_text(json.dumps(_stamp(payload), indent=2, default=str))


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
    # Prefer the DISPLAY panel (phase_b_fetch --display, prices through TODAY)
    # so this market-context series refreshes daily — the frozen research panel
    # (track_b_panel) stops at the 2026-06-30 cutoff and would freeze the chart.
    # Fall back to the frozen panel only if the display panel is absent (fresh
    # CI before the display-fetch step populates it). Display-only either way.
    display_panel = Path("data/cache/display_panel.parquet")
    panel_path = display_panel if display_panel.exists() else Path("data/cache/track_b_panel.parquet")
    us = pd.read_parquet(panel_path)
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
    # China-market milestones (region "cn") enter the same table as GLOBAL-CONTEXT
    # disclosure: they annotate the world around the US-only index chart above,
    # not the plotted series itself (e.g. the 2026-08-19 A-share session).
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
        # A股/中国宏观语境事件（region "cn"）——全球语境披露，非上图美国序列。
        {"date": "2025-10-23", "label": "二十届四中全会闭幕：「十五五」规划建议获通过", "type": "political", "region": "cn"},
        {"date": "2026-08-19", "label": "A股暴跌：沪指 -2.4% 失守 3900，创业板 -6.26%", "type": "crisis", "region": "cn"},
        {"date": "2026-08-19", "label": "宇树科技上市首日 +460%", "type": "ipo", "region": "cn"},
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
            "trade / Fed-independence), not personal ceremonies. China-market "
            "milestones (region 'cn') enter the event table as global-context "
            "disclosure: they annotate the world around the US-only index chart, "
            "not the plotted series itself. Display-only."
        ),
        "start_label": "2016 → · President ↔ Fed",
        "vix_series": vix_series,
        "market_series": market_series,
        "risk": risk_json,
        "events": events,
        "n_months": len(market_series),
        "date_range": [market_series[0]["month"], market_series[-1]["month"]] if market_series else [],
    }
    (WEB / "market_context.json").write_text(json.dumps(_stamp(payload), indent=2, default=str))


def _alfred_latest_series(path: Path) -> pd.DataFrame:
    """Latest-vintage (fully revised) series from an ALFRED json → DataFrame[date, value].

    For each observation date, keeps the row with the MAX ``realtime_start`` (the
    most-recently-published revision = the current public value). Robust across
    vintage styles: works whether ``realtime_end`` is ``'9999-12-31'`` (CPI/PAYEMS)
    or a dated cutoff (DFF). DISPLAY ONLY — revised series, NOT PIT-as-of.
    """
    d = json.loads(path.read_text())
    rows = [
        {"date": pd.Timestamp(o["date"]), "rts": str(o.get("realtime_start", "")), "value": float(o["value"])}
        for o in d.get("observations", [])
        if o.get("value") not in (".", "", None)
    ]
    if not rows:
        return pd.DataFrame(columns=["date", "value"]).set_index("date")
    df = pd.DataFrame(rows).sort_values(["date", "rts"]).drop_duplicates("date", keep="last")
    return df[["date", "value"]].set_index("date").sort_index()


def _monthly_points(s: pd.Series, ndigits: int = 2) -> list[dict]:
    """Serialize a date-indexed monthly Series → ``[{month, value}]`` (NaN dropped).

    Used by ``export_macro_drivers`` for every series so the dataKey="month"/"value"
    shape is uniform across the macro sub-panel charts.
    """
    return [
        {"month": d.strftime("%Y-%m"), "value": round(float(v), ndigits)}
        for d, v in s.dropna().items()
    ]


def export_macro_drivers() -> None:
    """Macro-driver sub-panel: the objective functions of the President↔Fed game.

    CPI YoY (price-stability mandate), nonfarm-payrolls YoY (max-employment
    mandate), and the Fed funds rate (DFF monthly mean — the policy lever).
    Source = ALFRED latest-vintage (fully revised) series. DISPLAY ONLY: the
    revised public values for context, NOT the PIT-as-of vintages the research
    pipeline uses — explicitly labeled so in the methodology.
    """
    cache = Path("data/cache")
    series: dict[str, list] = {}
    # Retain monthly Series for the derived real_rate computation below.
    cpi_yoy_s: pd.Series | None = None
    dff_m_s: pd.Series | None = None

    cpi_path = cache / "alfred_CPIAUCSL.json"
    if cpi_path.exists():
        cpi = _alfred_latest_series(cpi_path)
        cpi = cpi[cpi.index >= "2016-01-01"]
        if len(cpi) > 12:
            cpi_yoy_s = (cpi["value"] / cpi["value"].shift(12) - 1) * 100
            series["cpi_yoy"] = _monthly_points(cpi_yoy_s)

    payems_path = cache / "alfred_PAYEMS.json"
    if payems_path.exists():
        pay = _alfred_latest_series(payems_path)
        pay = pay[pay.index >= "2016-01-01"]
        if len(pay) > 12:
            pay_yoy = (pay["value"] / pay["value"].shift(12) - 1) * 100
            series["payems_yoy"] = _monthly_points(pay_yoy)

    dff_path = cache / "alfred_DFF.json"
    if dff_path.exists():
        dff = _alfred_latest_series(dff_path)  # daily
        dff = dff[dff.index >= "2016-01-01"]
        if not dff.empty:
            dff_m_s = dff["value"].resample("MS").mean()  # monthly mean of the daily effective rate
            series["fedfunds"] = _monthly_points(dff_m_s)

    # --- Display-only additions (no research-pipeline owner; see macro_display) ---
    # Trade-weighted dollar (policy → dollar → market transmission channel).
    # Daily series → monthly mean.
    dxy_path = cache / "alfred_DTWEXBGS.json"
    if dxy_path.exists():
        dxy = _alfred_latest_series(dxy_path)
        dxy = dxy[dxy.index >= "2016-01-01"]
        if not dxy.empty:
            series["dxy"] = _monthly_points(dxy["value"].resample("MS").mean())

    # 10Y−2Y Treasury spread (yield-curve recession watch). Daily → monthly mean.
    t10y2y_path = cache / "alfred_T10Y2Y.json"
    if t10y2y_path.exists():
        spr = _alfred_latest_series(t10y2y_path)
        spr = spr[spr.index >= "2016-01-01"]
        if not spr.empty:
            series["t10y2y"] = _monthly_points(spr["value"].resample("MS").mean())

    # Unemployment rate (max-employment mandate STOCK, vs PAYEMS flow). Monthly.
    unrate_path = cache / "alfred_UNRATE.json"
    if unrate_path.exists():
        un = _alfred_latest_series(unrate_path)
        un = un[un.index >= "2016-01-01"]
        if not un.empty:
            series["unrate"] = _monthly_points(un["value"])

    # Real policy rate = Fed funds − CPI YoY (the true stance). Both %, month-aligned.
    if dff_m_s is not None and cpi_yoy_s is not None:
        real = (dff_m_s - cpi_yoy_s).dropna()
        if not real.empty:
            series["real_rate"] = _monthly_points(real)

    if not series:
        # All ALFRED caches absent (fresh CI checkout / worktree without the
        # gitignored caches): preserve the tracked JSON — mirroring the
        # cot/form4/ipo 'retain last-committed value' convention. Writing the
        # awaiting_fetch placeholder here would clobber the committed live
        # panel (7 series) and silently hide the /regime cards.
        print(
            "[export-terminal] SKIP macro_drivers: no data/cache/alfred_*.json "
            "present (tracked JSON retains last-committed value)",
            flush=True,
        )
        return

    payload = {
        "status": "ok" if series else "awaiting_fetch",
        "series": series,
        "methodology": (
            "Macro drivers (display-only context). Latest-vintage (fully revised) "
            "ALFRED series — the standard public revised values, NOT the PIT-as-of "
            "vintages used in the research pipeline. CPI YoY = headline inflation "
            "(price-stability mandate); PAYEMS YoY = nonfarm payrolls growth "
            "(max-employment mandate flow); Fed funds = DFF monthly mean (policy "
            "lever); UNRATE = unemployment (max-employment mandate stock); DXY = "
            "trade-weighted dollar index (policy→dollar→market channel); T10Y2Y = "
            "10Y−2Y Treasury spread (yield-curve recession watch); real_rate = "
            "Fed funds − CPI YoY (the true policy stance). Visualizes the objective "
            "functions of the President↔Fed game. NOT a research claim."
        ),
    }
    (WEB / "macro_drivers.json").write_text(json.dumps(_stamp(payload), indent=2))


def export_ledger_audit() -> None:
    """Export a curated audit timeline of runs/ledger.jsonl (READ-ONLY).

    This surfaces Aionis's defining identity — ``config_committed BEFORE
    result`` — as a chronological, browser-renderable timeline on /discipline.
    It extracts only the claim-bearing rows (config_committed, confirmatory:first,
    oos_result, exploratory verdicts) and their minimal display fields; it never
    mutates the ledger (the append-only audit log is sacred). Non-claim rows
    (pre-run mocks, transient annotations) are skipped to keep the display honest
    and focused.
    """
    rows = _read_ledger_rows()
    if not rows:
        return
    # Events that carry a claim or a frozen-config commitment. Everything else
    # (prereg_reframe, universe_crosscheck, data_ingest, mock trials) is
    # scaffolding — omitting it keeps the timeline focused on what was frozen
    # and what the verdict was, not the bookkeeping.
    CLAIM_EVENTS = {
        "config_committed",
        "confirmatory:first",
        "oos_result",
        "exploratory",
        "phase_b_freeze",
    }
    entries: list[dict] = []
    for i, row in rows:
        event = row.get("event", "")
        if event not in CLAIM_EVENTS:
            continue
        sig = row.get("config_sig") or ""
        # Verdict/result extraction across the three real ledger shapes:
        #   (a) confirmatory:first — flat row with nested combined_ic.mean +
        #       jt_gate.look1_verdict (e.g. the climax #49 headline claim).
        #   (b) oos_result — a nested `result` dict with verdict + ic_diff_hac.
        #   (c) exploratory — flat top-level mean_diff / no verdict (notes only).
        # The prior version only handled (b) and a flat combined_ic scalar, which
        # is why the climax row #49 rendered with an empty metric: its IC is a
        # nested dict, not a scalar. Covering (a) makes the headline claim audible.
        verdict = ""
        metric = ""
        result = row.get("result")
        if isinstance(result, dict):
            verdict = str(result.get("verdict", ""))[:160]
            diff = result.get("ic_diff_hac")
            if isinstance(diff, dict) and "mean" in diff:
                metric = f"IC_diff={diff['mean']:.4f} (p={diff.get('p', '?')})"
        else:
            cic = row.get("combined_ic")
            if isinstance(cic, dict) and "mean" in cic:
                p_hac = cic.get("p_hac")
                p_str = f"{p_hac:.3f}" if isinstance(p_hac, (int, float)) else "?"
                metric = f"combined_IC={cic['mean']:.4f} (p={p_str})"
                jt = row.get("jt_gate") or {}
                look1 = jt.get("look1_verdict")
                verdict = look1 or verdict
            elif isinstance(cic, (int, float)):
                metric = f"combined_IC={cic:.4f}"
            elif isinstance(row.get("mean_diff"), (int, float)):
                metric = f"mean_diff={row['mean_diff']:.4f}"
        h6 = row.get("H6_deterministic")
        entries.append(
            {
                "row": i,
                "ts": row.get("ts", "")[:10],
                "event": event,
                "phase": row.get("phase", ""),
                "config_sig_short": sig[:8] if sig else "",
                "verdict": verdict,
                "metric": metric,
                "h6": bool(h6) if isinstance(h6, bool) else None,
                "frozen_before_result": event == "config_committed",
            }
        )
    payload = {
        "entries": entries,
        "n_total_rows": len(rows),
        "n_claim_rows": len(entries),
        "identity_note": (
            "config_committed rows always precede their matching result row in "
            "this timeline — that ordering is the anti-leakage contract: the "
            "frozen config's sha256 is logged before any OOS metric is observed."
        ),
    }
    (WEB / "ledger_audit.json").write_text(json.dumps(_stamp(payload), indent=2, default=str))


def export_headline_provenance() -> None:
    """Export the birth certificate of the headline claim (READ-ONLY).

    The terminal's hero number is ``combined rank-IC = -0.0088`` (ledger #49).
    Surfacing that number without its provenance leaves it un-anchored — a
    visitor cannot tell *which* frozen config produced it, *whether* the config
    was committed before the result, or *whether* H6 determinism holds. This
    export ties the hero metric to its exact ledger row, its freezing row (the
    config_committed that precedes it with the same sha256), and the empirical
    ts ordering that proves ``config_committed BEFORE result``. It never mutates
    the ledger; it only projects existing rows into a browser-renderable bundle.

    Resilient: scans for the first ``confirmatory:first`` row (does not hardcode
    a row number — those drift as the ledger grows), then pairs it with the last
    ``config_committed`` row sharing its sha256. Absent any confirmatory row, it
    emits a ``status: "awaiting_confirmatory"`` bundle so the hero degrades
    honestly rather than rendering a stale/hardcoded certificate.
    """
    rows = _read_ledger_rows()
    if not rows:
        return

    def _find(sig: str, event: str, *, before_row: int | None = None) -> tuple[int, dict] | None:
        candidates = [(r, d) for r, d in rows if d.get("event") == event]
        if sig:
            candidates = [(r, d) for r, d in candidates if (d.get("config_sig") or "").startswith(sig)]
        if before_row is not None:
            candidates = [(r, d) for r, d in candidates if r < before_row]
        return candidates[-1] if candidates else None

    result = _find_climax_row()
    if result is None:
        # No confirmatory claim yet — degrade honestly.
        (WEB / "headline_provenance.json").write_text(
            json.dumps(_stamp({"status": "awaiting_confirmatory"}), indent=2, default=str)
        )
        return
    result_row, result_d = result
    sig_full = result_d.get("config_sig") or ""
    freeze = _find(sig_full, "config_committed", before_row=result_row)
    cic = result_d.get("combined_ic")
    jt = result_d.get("jt_gate") or {}

    def _num(v: object) -> float | None:
        return float(v) if isinstance(v, (int, float)) else None

    payload = {
        "status": "ok",
        "ledger_row": result_row,
        "phase": result_d.get("phase", ""),
        "config_sig_short": sig_full[:8] if sig_full else "",
        "config_sig_source": result_d.get("config_sig_source", ""),
        "result_ts": result_d.get("ts", ""),
        "result_event": result_d.get("event", ""),
        "freeze": None,
        "headline": {
            "combined_ic": _num(cic.get("mean")) if isinstance(cic, dict) else None,
            "p_hac": _num(cic.get("p_hac")) if isinstance(cic, dict) else None,
            "ci_lo": _num(cic.get("ci_95_half") and cic["mean"] - cic["ci_95_half"]) if isinstance(cic, dict) else None,
            "ci_hi": _num(cic.get("ci_95_half") and cic["mean"] + cic["ci_95_half"]) if isinstance(cic, dict) else None,
            "n_months": _num(result_d.get("n_months_ic") or (cic.get("n") if isinstance(cic, dict) else None)),
            "jt_look1": jt.get("look1_verdict", ""),
            "h6_deterministic": bool(result_d.get("H6_deterministic")),
        },
        # The contract in numbers: freeze ts precedes result ts. We surface the
        # raw ts so the terminal can render the gap explicitly.
        "contract": {"freeze_before_result": False, "note": ""},
    }
    if freeze is not None:
        freeze_row, freeze_d = freeze
        payload["freeze"] = {
            "ledger_row": freeze_row,
            "ts": freeze_d.get("ts", ""),
            "event": freeze_d.get("event", ""),
            "config_sig_short": (freeze_d.get("config_sig") or "")[:8],
        }
        # Same sha256 + earlier ts = the contract proven on THIS headline.
        same_sig = bool(sig_full) and (freeze_d.get("config_sig") or "").startswith(sig_full[:8])
        earlier = freeze_d.get("ts", "") <= result_d.get("ts", "")
        payload["contract"] = {
            "freeze_before_result": bool(same_sig and earlier),
            "note": (
                "freeze sha256 == result sha256, and freeze ts precedes result ts"
                if same_sig and earlier
                else "ordering could not be verified"
            ),
        }
    (WEB / "headline_provenance.json").write_text(json.dumps(_stamp(payload), indent=2, default=str))


# --- data health (freshness/provenance map of every panel) --------------------
#
# Structural answer to "why doesn't panel X update": every committed panel is
# classified into exactly one freshness class, and its as_of is read from the
# panel's OWN timestamp fields at export time (never fabricated). Display-only.

_DH_FROZEN = "frozen"  # derived from frozen OOS artifacts (ledger #49 lineage)
_DH_DAILY = "daily"  # recomputed by the daily CI lane from live caches
_DH_CADENCE = "cadence"  # advances on the source's publication rhythm

# (key, json file, category) — as_of extracted per key by _dh_as_of below.
_DATA_HEALTH_MANIFEST: list[tuple[str, str, str]] = [
    ("metrics", "metrics.json", _DH_FROZEN),
    ("picks", "picks.json", _DH_FROZEN),
    ("shorts", "shorts.json", _DH_FROZEN),
    ("picks_meta", "picks_meta.json", _DH_FROZEN),
    ("sector_breakdown", "sector_breakdown.json", _DH_FROZEN),
    ("picks_backtest", "picks_backtest.json", _DH_FROZEN),
    ("ic_monthly", "ic_monthly.json", _DH_FROZEN),
    ("pick_conviction", "pick_conviction.json", _DH_FROZEN),
    ("model_health", "model_health.json", _DH_FROZEN),
    ("calibration_reliability", "calibration_reliability.json", _DH_FROZEN),
    ("power_floor", "power_floor.json", _DH_FROZEN),
    ("sigma_survey", "sigma_survey.json", _DH_FROZEN),
    ("bps_sweep", "bps_sweep.json", _DH_FROZEN),
    ("evidence", "evidence.json", _DH_FROZEN),
    ("stock_universe", "stock_universe.json", _DH_FROZEN),
    ("themes", "themes.json", _DH_DAILY),
    ("theme_signals", "theme_signals.json", _DH_DAILY),
    ("market_context", "market_context.json", _DH_DAILY),
    ("macro_drivers", "macro_drivers.json", _DH_DAILY),
    ("taco", "taco.json", _DH_DAILY),
    ("form4", "form4.json", _DH_DAILY),
    ("form8k", "form8k.json", _DH_DAILY),
    ("executives", "executives.json", _DH_DAILY),
    ("ipo", "ipo.json", _DH_DAILY),
    ("form_d", "form_d.json", _DH_DAILY),
    ("filing_stream", "filing_stream.json", _DH_DAILY),
    ("politician_trades", "politician_trades.json", _DH_DAILY),
    ("politician_trades_tx", "politician_trades_tx.json", _DH_DAILY),
    ("party_index", "party_index.json", _DH_DAILY),
    ("reddit", "reddit.json", _DH_DAILY),
    ("reddit_trending", "reddit_trending.json", _DH_DAILY),
    ("headline_provenance", "headline_provenance.json", _DH_DAILY),
    ("ledger_audit", "ledger_audit.json", _DH_DAILY),
    ("cot", "cot.json", _DH_CADENCE),
    ("smart_money", "smart_money.json", _DH_CADENCE),
    ("stakes_13g", "stakes_13g.json", _DH_DAILY),
    ("ark", "ark.json", _DH_DAILY),
    ("form13f", "form13f.json", _DH_CADENCE),
]


def _dh_read(fname: str):
    """Load a committed panel JSON defensively (missing/malformed → None)."""
    try:
        return json.loads((WEB / fname).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _dh_last_month_of_series(panel: dict) -> str | None:
    latest = None
    for series in panel.get("series", {}).values():
        for pt in series:
            if pt.get("month") and (latest is None or pt["month"] > latest):
                latest = pt["month"]
    return latest


def _dh_as_of(key: str, fname: str) -> str | None:
    """Extract each panel's own observation date. null = no date carried."""
    p = _dh_read(fname)
    if p is None:
        return None
    if key == "metrics":
        return p.get("latest_month")
    if key in {"picks", "shorts"}:
        pm = _dh_read("picks_meta.json")
        return pm.get("latest_date") if isinstance(pm, dict) else None
    if key == "picks_meta":
        return p.get("latest_date")
    if key == "sector_breakdown":
        dates = [d for d in p.get("latest_dates", {}).values() if d]
        return max(dates) if dates else None
    if key == "picks_backtest":
        months = [m.get("month") for m in p.get("months", []) if m.get("month")]
        return months[-1] if months else None
    if key == "ic_monthly":
        rows = [r.get("month") for r in p if isinstance(r, dict) and r.get("month")]
        return rows[-1] if rows else None
    if key == "pick_conviction":
        latest = p.get("latest")
        return latest.get("date") if latest else None
    if key == "stock_universe":
        dates = [d for d in p.get("as_of", {}).values() if d]
        return max(dates) if dates else None
    if key == "themes":
        freshness = p.get("freshness")
        if freshness:
            return freshness.get("latest")
        return p.get("as_of_date")
    if key == "theme_signals":
        return p.get("as_of_date")
    if key == "market_context":
        dr = p.get("date_range", [])
        return dr[-1] if dr else None
    if key == "macro_drivers":
        return _dh_last_month_of_series(p)
    if key == "taco":
        return p.get("latest_date")
    if key == "form4":
        recent = p.get("recent", [])
        return recent[0].get("date") if recent else None
    if key == "form8k":
        return p.get("as_of")
    if key == "executives":
        return p.get("as_of")
    if key == "ipo":
        return p.get("as_of")
    if key == "form_d":
        return p.get("as_of")
    if key == "filing_stream":
        return p.get("as_of")
    if key == "ark":
        return p.get("as_of")
    if key == "reddit_trending":
        ts = p.get("as_of")
        return ts.split("T")[0] if ts else None
    if key == "politician_trades":
        # as_of = latest as-filed FilingDate carried by the bulk FD.xml index.
        return p.get("as_of")
    if key == "politician_trades_tx":
        # as_of = latest filing date among the filings the transactions parse.
        return p.get("as_of")
    if key == "cot":
        return p.get("latest_date")
    if key == "smart_money":
        return p.get("latest_date")
    if key == "stakes_13g":
        return p.get("as_of")
    if key == "form13f":
        return p.get("as_of")
    if key == "headline_provenance":
        ts = p.get("result_ts")
        return ts.split("T")[0] if ts else None
    # model_health / calibration_reliability / power_floor / sigma_survey /
    # bps_sweep / evidence / reddit / ledger_audit: no observation date field.
    return None


# Planned-but-not-built panels (honest disclosure, mirrors the xiaoyinsi
# x-status: planned pattern): nothing is fetched, parsed or served for these
# keys today. Shared by data_health (key + note) and api_catalog (planned
# endpoints) from ONE definition so the two can never drift apart.
_PLANNED_PANELS: list[dict[str, str]] = [
    # politician-trades SHIPPED 2026-08-21 (politician_trades panel, House PTR
    # filing-stream level — 7-gate PASS in docs/data-intake-congress-stock-act.md)
    # — graduated out of planned into a live panel. List kept (empty) so the
    # shared data_health/api_catalog definition stays the single source of truth.
]


def _dh_days_since(date_str: str | None) -> int | None:
    """Whole days between today (UTC) and a YYYY-MM-DD[*] panel date."""
    if not date_str:
        return None
    try:
        d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    return (datetime.now(timezone.utc).date() - d).days


def _source_health() -> dict:
    """Field-level quality metrics for sources with known gaps (counted)."""
    sm = _dh_read("smart_money.json") or {}
    recent = sm.get("recent_filings") or []
    sg = _dh_read("stakes_13g.json") or {}
    sg_filings = sg.get("filings") or []
    reddit = _dh_read("reddit.json") or {}
    picks = reddit.get("picks") or []
    cot = _dh_read("cot.json") or {}
    return {
        "smart_money": {
            "ticker_null": sum(1 for r in recent if not r.get("ticker")),
            "n_recent": len(recent),
            "days_since_latest": _dh_days_since(sm.get("latest_date")),
        },
        "stakes_13g": {
            "ticker_null": sum(1 for r in sg_filings if not r.get("ticker")),
            "filer_unresolved": sum(
                1 for r in sg_filings if str(r.get("filer", "")).startswith("(")
            ),
            "n_filings": len(sg_filings),
            "days_since_latest": _dh_days_since(sg.get("as_of")),
        },
        "reddit": {
            "bull_ratio_null": sum(1 for p in picks if p.get("bull_ratio") is None),
            "n_picks": len(picks),
        },
        "cot": {
            "weeks_since_latest": (
                None if _dh_days_since(cot.get("latest_date")) is None
                else _dh_days_since(cot.get("latest_date")) // 7
            ),
        },
    }


def export_data_health() -> None:
    """Freshness + provenance map of every terminal panel (display-only).

    Classifies each committed JSON into frozen / daily / cadence and reads its
    as_of from the panel's own fields. This is the structural, always-current
    answer to "why is this number not updating": frozen panels advancing would
    BE the leakage (rerun-to-significance); the map makes that contract visible
    instead of asking visitors to infer it from scattered as_of chips.
    """
    panels = []
    for key, fname, category in _DATA_HEALTH_MANIFEST:
        as_of = _dh_as_of(key, fname)
        # snapshot_ts = when this panel's committed JSON was last written by the
        # export lane (proxy for "refresh lane touched it"), distinct from the
        # panel's own data as_of.
        payload = _dh_read(fname)
        snap = payload.get("snapshot_ts") if isinstance(payload, dict) else None
        if isinstance(payload, list):
            snap = None
        panels.append({
            "key": key,
            "file": fname,
            "category": category,
            "as_of": as_of,
            "exported_at": snap.split("T")[0] if snap else None,
            "present": payload is not None,
        })
    summary = {
        "n_panels": len(panels),
        "n_frozen": sum(1 for p in panels if p["category"] == _DH_FROZEN),
        "n_daily": sum(1 for p in panels if p["category"] == _DH_DAILY),
        "n_cadence": sum(1 for p in panels if p["category"] == _DH_CADENCE),
    }
    payload = {
        "status": "ok",
        "panels": panels,
        "summary": summary,
        "source_health": _source_health(),
        "planned": [
            {"key": p["key"], "note": p["note"]} for p in _PLANNED_PANELS
        ],
        "methodology": (
            "Freshness/provenance map of every terminal panel. frozen = derived "
            "from frozen OOS artifacts (ledger #49 lineage): the daily lane "
            "deliberately does NOT advance these — recomputing them from newer "
            "data would be rerun-to-significance. daily = recomputed by each CI "
            "refresh from live caches. cadence = advances on its source's "
            "publication rhythm (CFTC weekly, price caches ~5-day grace, EDGAR "
            "filing rhythm). as_of is read from each panel's own timestamp "
            "fields; null = the panel carries no observation date (static "
            "research artifact). The only legal way frozen numbers move "
            "forward: E3 forward-live accumulation or a new pre-registered "
            "phase. source_health quantifies field-level quality on the "
            "committed JSONs (smart_money ticker nulls = filings on unlisted "
            "targets honestly left empty; reddit bull_ratio nulls = sentiment "
            "not yet gradable in the accumulating window; cot staleness in "
            "weeks vs the Friday publication rhythm). planned lists panels "
            "that are NOT built — no fetcher, no data, no endpoint payload — "
            "disclosed so the panel count is never mistaken for coverage."
        ),
    }
    (WEB / "data_health.json").write_text(json.dumps(_stamp(payload), indent=2))


# --- API catalog (public static data API over the committed panels) ----------
#
# Imitation of the xiaoyinsi datahub discipline (learned from its /api-docs):
# every data path carries provenance metadata — for Aionis that means the
# 7-gate intake facts (license + primary source) plus the freshness class.
# The panels stay verbatim JSON; this catalog is the machine-readable index.

# key → (license, primary source). Mirrors docs/data-intake-*.md; keep in sync.
_API_LICENSE: dict[str, tuple[str, str]] = {
    "metrics": ("Aionis research artifacts (repo MIT)", "frozen OOS scores, ledger #49 lineage"),
    "picks": ("Aionis research artifacts (repo MIT)", "frozen OOS scores + Platt calibration"),
    "shorts": ("Aionis research artifacts (repo MIT)", "frozen OOS scores + Platt calibration"),
    "picks_meta": ("Aionis research artifacts (repo MIT)", "calibration meta on realized OOS pairs"),
    "sector_breakdown": ("Aionis research artifacts (repo MIT)", "frozen OOS scores by sector"),
    "picks_backtest": ("Aionis research artifacts (repo MIT)", "realized OOS picks vs base, 131 months"),
    "ic_monthly": ("Aionis research artifacts (repo MIT)", "confirmatory monthly rank-IC series"),
    "pick_conviction": ("Aionis research artifacts (repo MIT)", "cross-sectional score dispersion"),
    "model_health": ("Aionis research artifacts (repo MIT)", "PSI + rolling IC on realized OOS"),
    "calibration_reliability": ("Aionis research artifacts (repo MIT)", "walk-forward calibration audit"),
    "power_floor": ("Aionis research artifacts (repo MIT)", "sigma survey / power analysis"),
    "sigma_survey": ("Aionis research artifacts (repo MIT)", "observed vs pure-noise sigma"),
    "bps_sweep": ("Aionis research artifacts (repo MIT)", "net-cost sensitivity sweep"),
    "evidence": ("Aionis research artifacts (repo MIT)", "research ledger evidence table"),
    "stock_universe": ("Aionis research artifacts (repo MIT)", "per-stock frozen readout over OOS scores"),
    "themes": (
        "Tiingo/Alpaca free tier (vendor ToS, display-only) + GDELT open data",
        "daily prices, fundamentals, GDELT news sentiment, ALFRED macro",
    ),
    "theme_signals": (
        "Tiingo/Alpaca free tier (vendor ToS, display-only) + GDELT open data",
        "per-theme signal aggregates on the display panel",
    ),
    "market_context": (
        "Tiingo/Alpaca free tier (vendor ToS, display-only) + FRED (public domain)",
        "equal-weight index monthly series + VIX + labeled events",
    ),
    "macro_drivers": ("FRED/ALFRED — U.S. Government public domain", "CPI, payrolls, rates, DFF vintages"),
    "taco": ("FRED (public domain) + labeled public news events", "VIX monthly + Trump-policy event table"),
    "form4": ("U.S. SEC EDGAR — public domain", "Form 4 XML, filed-date PIT"),
    "form8k": ("U.S. SEC EDGAR — public domain", "Form 8-K primary docs, filed-date PIT, item-classified"),
    "executives": (
        "U.S. SEC EDGAR — public domain",
        "Form 8-K Item 5.02 officer-changes stream (derived from form8k, "
        "filed-date PIT; person-level extraction deferred)",
    ),
    "ipo": (
        "U.S. SEC EDGAR — public domain",
        "IPO registration/pricing stream (S-1/S-1/A + 424B4) via EFTS "
        "form-level queries, filed-date PIT; offer terms not extracted",
    ),
    "form_d": (
        "U.S. SEC EDGAR — public domain",
        "Form D exempt-offering notices (D + D/A) via EFTS form-level "
        "queries, filed-date PIT; offering amounts not extracted",
    ),
    "filing_stream": (
        "Aionis-derived from U.S. SEC EDGAR public-domain panels",
        "unified cross-form feed (4 / 8-K / S-1 family / 424B4 / D / SC 13D / "
        "SC 13G) merged from the terminal's own committed panels",
    ),
    "politician_trades": (
        "U.S. House Clerk — public domain",
        "STOCK Act PTR filing index (House-only, filing-stream level; "
        "transactions remain in the source PDFs)",
    ),
    "politician_trades_tx": (
        "U.S. House Clerk — public domain",
        "STOCK Act PTR transactions parsed from the source PDFs (House-only; "
        "statutory amount bands; parse failures disclosed)",
    ),
    "party_index": (
        "Aionis-derived from U.S. House Clerk public-domain PTR parses",
        "monthly D-vs-R net-direction opposition share + trailing-90d "
        "count-weighted follow portfolios (signal lists, no returns)",
    ),
    "reddit": ("Reddit public Atom RSS — Reddit ToS, display-only", "retail mention counts, forward-only"),
    "reddit_trending": (
        "ApeWisdom free public API (apewisdom.io) — vendor ToS, display-only",
        "Reddit trending-stocks board: rank/mentions/upvotes + 24h lags, "
        "verbatim first-party fields, today-snapshot only",
    ),
    "headline_provenance": ("Aionis append-only ledger (repo MIT)", "ledger.jsonl freeze→result pairing"),
    "ledger_audit": ("Aionis append-only ledger (repo MIT)", "ledger.jsonl claim-row timeline"),
    "cot": ("U.S. CFTC — public domain", "Commitments of Traders legacy futures, weekly"),
    "smart_money": ("U.S. SEC EDGAR — public domain", "13D/G filings via EFTS, filed-date PIT"),
    "stakes_13g": (
        "U.S. SEC EDGAR — public domain",
        "SC 13G/G-A passive-stake stream via the daily crawler index "
        "(EFTS froze on Schedule 13 after 2024-12-17), filed-date PIT; "
        "ownership % / state machine not parsed",
    ),
    "form13f": ("U.S. SEC EDGAR — public domain", "13F-HR quarterly holdings XML, filed-date PIT, whole-USD values"),
    "ark": (
        "ARK Invest official fund CSVs — publicly published daily",
        "8-ETF Full Holdings CSVs from assets.ark-funds.com (browser-verified "
        "endpoint URLs; top-10 by weight + family overlap; skips disclosed)",
    ),
    "data_health": ("Aionis-generated (repo MIT)", "freshness/provenance map over all panels"),
}


def export_api_catalog() -> None:
    """Machine-readable index of the public static data API (display-only).

    Pairs each committed panel with its 7-gate intake facts (license, primary
    source) and its freshness class + as_of (read from data_health.json, the
    single source of truth). Consumers of the deployed JSON API get the same
    provenance discipline the terminal renders: where a number comes from,
    under what license, and whether it should be expected to advance.
    """
    dh = _dh_read("data_health.json")
    if not isinstance(dh, dict) or "panels" not in dh:
        raise FileNotFoundError("data_health.json (run export_data_health first)")
    endpoints = []
    for p in dh["panels"]:
        license_, source = _API_LICENSE.get(
            p["key"], ("unverified — do not ingest", "unknown")
        )
        endpoints.append({
            "key": p["key"],
            "file": p["file"],
            "path": f"/api/v1/panels/{p['file']}",
            "method": "GET",
            "status": "available",
            "freshness": p["category"],
            "as_of": p["as_of"],
            "license": license_,
            "source": source,
        })
    # Planned-but-not-built endpoints (honest x-status: planned disclosure —
    # same shape as available ones so consumers can branch on status alone).
    # as_of=null: no observation exists by construction.
    endpoints.extend({
        "key": pl["key"],
        "file": pl["file"],
        "path": f"/api/v1/panels/{pl['file']}",
        "method": "GET",
        "status": "planned",
        "freshness": "planned",
        "as_of": None,
        "license": pl["license"],
        "source": pl["source"],
    } for pl in _PLANNED_PANELS)
    payload = {
        "status": "ok",
        "base_note": (
            "Static JSON contract served straight from GitHub Pages — read-only, "
            "no auth, no server. Panel files are the payload verbatim; this "
            "catalog is the meta layer."
        ),
        "endpoints": endpoints,
        "live_prices": {
            "note": (
                "Live quotes are a separate display-only Cloudflare Worker; "
                "they must never feed the research pipeline."
            ),
            "paths": [
                {"method": "GET", "path": "/api/prices/us?tickers=AAPL,MSFT"},
                {"method": "GET", "path": "/api/prices/cn?tickers=sh.688041"},
            ],
            "server": "https://api.aionis-prices.workers.dev",
        },
        "methodology": (
            "Public static data API over the terminal's committed panels "
            "(display-only). Every endpoint carries its 7-gate intake facts: "
            "license + primary source, plus the freshness class (daily / "
            "cadence / frozen). Frozen endpoints derive from frozen OOS "
            "artifacts (ledger #49 lineage) and deliberately do NOT advance — "
            "consuming them expecting daily updates misreads the contract. "
            "Endpoints with status=planned are NOT built: the path is a "
            "reserved future location, no payload is served, as_of is null, "
            "and the license/source describe the primary source the future "
            "fetcher would use. Research ingestion of any endpoint requires "
            "the full 7-gate rubric (docs/data-intake-rubric.md); the "
            "live-prices worker is display-only and must never enter the OOS "
            "pipeline."
        ),
    }
    (WEB / "api_catalog.json").write_text(json.dumps(_stamp(payload), indent=2))


# --- stock universe (per-stock view over the frozen OOS scores) ---------------


def export_stock_universe() -> None:
    """Per-stock aggregates over the frozen confirmatory OOS scores (display-only).

    One row per ticker in each region's latest OOS month: latest score,
    Platt-calibrated prob_up (same contract as export_picks), rank within the
    region, rank change vs the previous month, trailing-12m score series
    (aligned on a shared month grid with nulls for the other region's calendar),
    and corroboration counts joined from the smart-money / insider / retail
    panels. Powers /stock/[ticker] drill-down pages. Recomputing from newer
    data is forbidden (rerun-to-significance): the panel is a frozen-readout
    view, refreshed only when the underlying research surface legitimately
    advances (new frozen phase or E3 forward-live).
    """
    from aionis.eval.score_calibration import calibrate_latest_month

    df = pd.read_parquet("runs/track_c_confirmatory_oos_scores.parquet")
    df["date"] = pd.to_datetime(df["date"])
    meta = _load_ticker_metadata()

    us_panel_path = Path("data/cache/track_b_panel.parquet")
    cn_panel_path = Path("data/cache/cn_price_panel.parquet")
    us_panel = pd.read_parquet(us_panel_path) if us_panel_path.exists() else pd.DataFrame()
    cn_panel = pd.read_parquet(cn_panel_path) if cn_panel_path.exists() else pd.DataFrame()
    calibration = calibrate_latest_month(df, us_panel, cn_panel)

    prob_lookup: dict[tuple[str, str], float] = {}
    region_latest: dict[str, pd.Timestamp] = {}
    for r, payload in calibration["regions"].items():
        if "latest" not in payload:
            continue
        region_latest[r] = pd.Timestamp(payload["latest_date"])
        for _, row in payload["latest"].iterrows():
            prob_lookup[(r, row["ticker"])] = float(row["prob_up"])

    # Shared month grid: union of each region's trailing 12 OOS months.
    month_grid: list[str] = []
    region_months: dict[str, list[pd.Timestamp]] = {}
    for r in region_latest:
        rdates = sorted(d for d in df[df["region"] == r]["date"].unique())
        region_months[r] = rdates[-12:]
    for rdates in region_months.values():
        for d in rdates:
            label = pd.Timestamp(d).strftime("%Y-%m")
            if label not in month_grid:
                month_grid.append(label)
    month_grid.sort()

    # Corroboration joins (same committed panels /confirmation renders).
    sm = _dh_read("smart_money.json") or {}
    f4 = _dh_read("form4.json") or {}
    rd = _dh_read("reddit.json") or {}
    sm_by_ticker: dict[str, list[dict]] = {}
    for f in sm.get("recent_filings", []):
        t = f.get("ticker")
        if t:
            sm_by_ticker.setdefault(t, []).append(f)
    f4_by_ticker: dict[str, list[dict]] = {}
    for f in f4.get("recent", []):
        t = f.get("ticker")
        if t:
            f4_by_ticker.setdefault(t, []).append(f)
    rd_by_ticker: dict[str, dict] = {}
    for rk in rd.get("picks", []):
        rd_by_ticker[rk["ticker"]] = rk

    meta_idx = {}
    if not meta.empty:
        meta_idx = {
            str(row["ticker"]): (row["name"], row["sector"])
            for _, row in meta.iterrows()
        }

    stocks: list[dict] = []
    for r, latest in region_latest.items():
        r_df = df[(df["region"] == r) & (df["date"] == latest)].copy()
        if r_df.empty:
            continue
        r_df["rank"] = r_df["score"].rank(ascending=False, method="first").astype(int)
        prev_idx = sorted(df[df["region"] == r]["date"].unique()).index(latest) - 1
        prev_rank = {}
        if prev_idx >= 0:
            prev_date = sorted(df[df["region"] == r]["date"].unique())[prev_idx]
            # Region-scoped: US/CN month-ends coincide often — an unscoped date
            # filter ranks a mixed-region frame (bug found via TROW rank_change
            # 829 > n_region 492).
            prev_df = df[(df["region"] == r) & (df["date"] == prev_date)].copy()
            prev_df["r"] = prev_df["score"].rank(ascending=False, method="first").astype(int)
            prev_rank = dict(zip(prev_df["ticker"], prev_df["r"], strict=True))
        # Trailing scores aligned to the shared month grid (null = month not in
        # this region's calendar / ticker absent that month).
        hist = df[(df["region"] == r) & (df["date"].isin(region_months[r]))]
        hist_map = {
            (t, pd.Timestamp(d).strftime("%Y-%m")): float(s)
            for t, d, s in zip(hist["ticker"], hist["date"], hist["score"], strict=True)
        }
        n_region = len(r_df)
        for _, row in r_df.iterrows():
            t = str(row["ticker"])
            name, sector = meta_idx.get(t, ("", ""))
            sm_hits = sm_by_ticker.get(t, [])
            f4_hits = f4_by_ticker.get(t, [])
            rd_hit = rd_by_ticker.get(t)
            prev = prev_rank.get(t)
            stocks.append({
                "ticker": t,
                "region": r,
                "name": name,
                "sector": sector,
                "score": round(float(row["score"]), 3),
                "prob_up": round(prob_lookup.get((r, t), 0.5), 3),
                "rank": int(row["rank"]),
                "n_region": n_region,
                "rank_change": (int(prev) - int(row["rank"])) if prev is not None else None,
                "scores": [
                    round(hist_map[(t, m)], 3) if (t, m) in hist_map else None
                    for m in month_grid
                ],
                "smart_money_n": len(sm_hits) or None,
                "smart_money_latest": sm_hits[0]["date"] if sm_hits else None,
                "form4_n": len(f4_hits) or None,
                "form4_latest": f4_hits[0]["date"] if f4_hits else None,
                "reddit_mentions": int(rd_hit["mentions"]) if rd_hit else None,
            })
    stocks.sort(key=lambda s: (s["region"], -s["score"]))
    if not stocks:
        committed_su = _committed_json("stock_universe.json")
        if committed_su and committed_su.get("stocks"):
            # Degenerate calibration (price-panel caches absent locally) wrote
            # n_stocks=0 on 2026-08-22 and cost a restore — retain the frozen
            # universe instead (it only legitimately advances with a new
            # frozen phase / E3, never from cache availability).
            _skip_retain("stock_universe", "empty universe (calibration degenerate)")
            return
    payload = {
        "status": "ok",
        "as_of": {r: pd.Timestamp(d).strftime("%Y-%m-%d") for r, d in region_latest.items()},
        "n_stocks": len(stocks),
        "months": month_grid,
        "stocks": stocks,
        "methodology": (
            "Per-stock view assembled from the frozen confirmatory OOS scores "
            "(ledger #49 lineage) — display-only. score / prob_up / rank are the "
            "frozen model readout for each region's latest OOS month (US and CN "
            "PIT calendars differ; see as_of per region). prob_up = "
            "Platt-calibrated P(forward month up) on realized OOS history — NOT "
            "investment advice; the research verdict is NULL (combined rank-IC "
            "−0.0088), so probabilities cluster near the base rate. The "
            "trailing series is the model's own monthly cross-sectional score "
            "for this ticker. Corroboration counts join the smart-money (13D), "
            "insider (Form 4) and retail (Reddit) panels by ticker. This panel "
            "must NOT be recomputed from newer data (rerun-to-significance): it "
            "advances only with a new frozen phase or E3 forward-live."
        ),
    }
    # Compact separators: 1,421 per-stock rows with trailing series would be
    # ~1MB pretty-printed; compact keeps the dedicated stock-page chunk lean.
    (WEB / "stock_universe.json").write_text(
        json.dumps(_stamp(payload), separators=(",", ":"), allow_nan=False)
    )


def export_form13f() -> None:
    """SEC 13F-HR star-manager quarterly holdings (display-only, exploratory).

    Reads ``data/cache/form13f_aggregate.parquet`` (gitignored; produced by
    ``scripts/form13f_fetch.py`` — 40 verified celebrity managers × the 2 most
    recent distinct report quarters). Public domain (17 U.S.C. §105);
    filing-date PIT; quarterly cadence; ``value`` as filed in the EDGAR 2014+
    XML (whole USD). Issuer→ticker links are EXACT normalized-name matches
    (case/punctuation/apostrophes/legal suffixes — see
    ``aionis.ingest.form13f.normalize_issuer_name``) against two offline
    sources: the terminal's committed US stock universe, then the SEC
    ``company_tickers.json`` snapshot cached by ``aionis.ingest.cik_resolver``
    (multi-CIK ambiguous names dropped — no fuzzy guessing). As-filed
    abbreviations ("BANK OF AMER CORP") and truncated 20-char legacy names
    stay unmatched and render as plain text (honest partial coverage).
    ``category`` (value/growth/activist/macro/quant/china_background/other) is
    editorial curation written in the fetch registry — NOT a SEC data-source
    field (disclosed in the methodology string).
    """
    from aionis.ingest.form13f import (
        build_issuer_ticker_map,
        compute_changes,
        normalize_issuer_name,
    )

    fp = Path("data/cache/form13f_aggregate.parquet")
    if not fp.exists():
        # CI fresh checkout / fetch failed: preserve the tracked JSON, don't
        # overwrite real data with an empty awaiting payload.
        print(
            "[export-terminal] SKIP form13f: data/cache/form13f_aggregate.parquet "
            "not present (tracked JSON retains last-committed value)",
            flush=True,
        )
        return

    df = pd.read_parquet(fp)

    # CUSIP→ticker is not available from EDGAR; link by normalized issuer NAME
    # instead. Layer 1 — the committed US stock universe (smallest ticker wins
    # a share-class collision, e.g. GOOG vs GOOGL — disclosed limitation).
    su = _dh_read("stock_universe.json") or {}
    name_to_ticker: dict[str, str] = {}
    for s in su.get("stocks", []):
        if s.get("region") != "us" or not s.get("name"):
            continue
        key = normalize_issuer_name(s["name"])
        if not key:
            continue
        if key not in name_to_ticker or str(s["ticker"]) < name_to_ticker[key]:
            name_to_ticker[key] = str(s["ticker"])

    # Layer 2 — the SEC company_tickers snapshot (current, NOT as-of-filing;
    # a display label + stock-page link only, never a research input). Names
    # claimed by 2+ CIKs are dropped as ambiguous by build_issuer_ticker_map.
    raw_fp = Path("data/cache/cik_resolver_raw.json")
    if raw_fp.exists():
        try:
            snap = json.loads(raw_fp.read_text())
            edgar_map = build_issuer_ticker_map(
                [
                    (str(v["title"]), int(v["cik_str"]), str(v["ticker"]))
                    for v in snap.values()
                    if isinstance(v, dict) and v.get("ticker") and v.get("title")
                ]
            )
        except (json.JSONDecodeError, AttributeError, ValueError):
            edgar_map = {}
    else:
        edgar_map = {}

    def _ticker_for(issuer: str) -> str | None:
        key = normalize_issuer_name(issuer)
        return name_to_ticker.get(key) or edgar_map.get(key)

    manager_payloads: list[dict] = []
    for cik, sub in df.groupby("cik"):
        quarters = sorted(sub["quarter"].unique(), reverse=True)
        cur_lines = sub[sub["quarter"] == quarters[0]]
        # One issuer may span several as-filed lines (multiple otherManager
        # tranches); merge same-(cusip, option) lines into one position so
        # top10 / n_positions count POSITIONS, not tranche rows. Keyed on
        # CUSIP+option (NOT title_class): the same CUSIP is the same security,
        # and filers' class-label strings drift across quarters.
        cur = (
            cur_lines.groupby(["cusip", "option_type"], as_index=False)
            .agg(
                issuer=("issuer", "first"),
                title_class=("title_class", "first"),
                value_usd=("value_usd", "sum"),
                shares=("shares", "sum"),
            )
        )
        prev = sub[sub["quarter"] == quarters[1]] if len(quarters) > 1 else pd.DataFrame()
        total_value = float(cur["value_usd"].sum())
        # Up to 50 positions (the whole book for most 13F filers) — the
        # xiaoyinsi-alignment visible-book granularity; concentration math and
        # the /stock holders reverse-lookup both consume the same list.
        positions = []
        for _, r in cur.nlargest(50, "value_usd").iterrows():
            positions.append({
                "issuer": str(r["issuer"]),
                "cusip": str(r["cusip"]),
                "title": str(r.get("title_class", "")),
                "option": str(r.get("option_type", "")),
                "value": round(float(r["value_usd"]), 0),
                "shares": round(float(r["shares"]), 0),
                "pct": round(float(r["value_usd"]) / total_value * 100.0, 2) if total_value else 0.0,
                "ticker": _ticker_for(str(r["issuer"])),
            })
        changes = []
        for ch in compute_changes(prev, cur)[:20]:
            changes.append({
                "issuer": ch["issuer"],
                "cusip": ch["cusip"],
                "title": ch["title"],
                "option": ch["option"],
                "direction": ch["direction"],
                "delta_pct": ch["delta_pct"],
                # Whole-USD value delta (cur − prev, both sides kept by the
                # frame diff): full position value for new/exited, plain
                # difference for increased/reduced (sign may oppose delta_pct
                # on price drift).
                "delta_value": round(float(ch["delta_value"]), 0),
                "ticker": _ticker_for(ch["issuer"]),
            })
        manager_payloads.append({
            "cik": f"{int(cik):010d}",
            "name": str(sub["manager_name"].iloc[0]),
            "zh_name": (
                zh if (zh := sub["zh_name"].iloc[0]) is not None and str(zh) != "nan" else None
            ) if "zh_name" in sub else None,
            "category": (
                str(cat) if pd.notna(cat := sub["category"].iloc[0]) else "other"
            ) if "category" in sub else "other",
            "quarter": str(quarters[0]),
            "filed": str(cur_lines["filing_date"].max()),
            "n_positions": int(len(cur)),
            "total_value": round(total_value, 0),
            "positions": positions,
            "changes": changes,
        })

    # Biggest portfolio first (display ordering; deterministic on ties).
    manager_payloads.sort(key=lambda m: (-m["total_value"], m["cik"]))
    n_linked = sum(
        1
        for m in manager_payloads
        for h in m["positions"]
        if h["ticker"]
    )
    n_top = sum(len(m["positions"]) for m in manager_payloads)
    cat_counts: dict[str, int] = {}
    for m in manager_payloads:
        cat_counts[m["category"]] = cat_counts.get(m["category"], 0) + 1
    payload = {
        "status": "ok",
        "as_of": str(df["quarter"].max()),
        "managers": manager_payloads,
        "ticker_coverage": f"{n_linked}/{n_top}",
        "category_counts": cat_counts,
        "methodology": (
            "SEC Form 13F-HR quarterly institutional holdings — the legally "
            "mandated public report (public domain, 17 U.S.C. §105) every "
            "institutional manager with >=US$100M discretion must file within "
            "45 days of quarter-end. Panel shows a bounded subset of ~40 star "
            "managers (CIKs verified against EDGAR submissions JSON "
            "2026-08-22; candidates not verifiable as actively filing — e.g. "
            "Scion, Greenlight, Omega Advisors, Pabrai — were honestly "
            "dropped), latest quarter top-10 holdings plus "
            "quarter-over-quarter frame diff (new/increased/reduced/exited on "
            "share counts, with a whole-USD value delta = current − prior "
            "quarter as-filed value; full position value on new/exited, and "
            "on increased/reduced the value sign may oppose the share move — "
            "price drift). Values are as filed in the EDGAR 2014+ "
            "information-table XML (whole USD — the 'expressed in thousands' "
            "note is the legacy HTML rendering); same-(CUSIP, class, option) "
            "tranches merged into one position; shares as filed (SH lines; "
            "option lines flagged PUT/CALL). Filing-date point-in-time; "
            "amendments supersede (latest filing per report quarter wins). "
            "Issuer→ticker links are exact normalized-name matches "
            "(case/punctuation/apostrophes/legal suffixes) against the "
            "terminal's US stock universe and the SEC company_tickers "
            "snapshot (current, not as-of-filing; ambiguous multi-entity "
            "names dropped) — EDGAR infotables carry CUSIPs, not tickers, "
            "and as-filed abbreviations stay unmatched plain text. The "
            "value/growth/activist/macro/quant/china_background/other "
            "category tags are HUMAN-CURATED editorial metadata written in "
            "the fetch registry — they do NOT exist in any SEC data source. "
            "Display-only, not a research claim; NOT part of any OOS "
            "pipeline."
        ),
    }
    (WEB / "form13f.json").write_text(json.dumps(_stamp(payload), indent=2, default=str))
    print(
        f"[export-terminal] form13f: {len(manager_payloads)} managers, "
        f"as_of {payload['as_of']}, ticker link coverage {payload['ticker_coverage']}",
        flush=True,
    )


def export_form8k() -> None:
    """SEC Form 8-K material-event stream (display-only, exploratory).

    Reads ``data/cache/form8k_aggregate.parquet`` (gitignored; produced by
    ``scripts/form8k_fetch.py`` — 25 large-cap issuers, fixed window from
    2026-05-01). Events carry the legally mandated 8-K item list
    (regex-extracted from the primary document, entity-spellings normalized)
    and ONE category via a rare-material-first precedence table. Docs the
    classifier cannot read are counted as ``unclassified`` — never guessed.
    """
    fp = Path("data/cache/form8k_aggregate.parquet")
    if not fp.exists():
        print(
            "[export-terminal] SKIP form8k: data/cache/form8k_aggregate.parquet "
            "not present (tracked JSON retains last-committed value)",
            flush=True,
        )
        return

    df = pd.read_parquet(fp)
    by_cat: dict[str, int] = df["category"].value_counts().to_dict()
    events = []
    # Bounded 50-issuer universe (~2.6k events/yr worst case); the cap is a
    # long-term growth guard, NOT a display slice — by_category/unclassified
    # count the full frame, so a cap hit would desync counts vs the visible
    # list and the contract test (len(events) == total) fails LOUDLY rather
    # than silently truncating.
    for _, r in df.head(300).iterrows():
        events.append({
            "ticker": str(r["ticker"]),
            "company": str(r["company"]),
            "filing_date": str(r["filing_date"]),
            "form": str(r["form"]),
            "items": [i for i in str(r["items"]).split(",") if i],
            "category": str(r["category"]),
            "doc_url": str(r["doc_url"]),
        })
    payload = {
        "status": "ok",
        "as_of": str(df["filing_date"].max()),
        "window": {"start": str(df["filing_date"].min()), "end": str(df["filing_date"].max())},
        "issuers": int(df["ticker"].nunique()),
        "total": int(len(df)),
        "unclassified": int(by_cat.get("unclassified", 0)),
        "by_category": {k: int(v) for k, v in sorted(by_cat.items())},
        "events": events,
        "methodology": (
            "SEC Form 8-K current reports — the legally mandated material-event "
            "disclosure (public domain, 17 U.S.C. §105), due within 4 business "
            "days of the event. Panel streams a bounded 50 large-cap issuer "
            "set (5 mega-cap seed + v2 20 + v3 25 across financials, payments, "
            "healthcare, staples, energy, industrials, tech/comm — breadth "
            "expansions 2026-08-22; still bounded, NOT full market; XOM "
            "carries both its pre-succession CIK and the 2026-07-01 8-K12B "
            "successor entity) "
            "since "
            "2026-05-01; each row links the EDGAR primary document. Items are "
            "regex-extracted from the primary doc (nbsp/thin-space entities "
            "normalized) and mapped to ONE category by a rare-material-first "
            "precedence (delisting > merger completion > control change > "
            "non-reliance > officer changes > ... > exhibits); the full item "
            "list is preserved per row. Documents whose items cannot be "
            "extracted are counted as unclassified — never guessed. "
            "Filing-date point-in-time; 8-K/A amendments are new accessions "
            "(immutable). Display-only, not a research claim; NOT part of "
            "any OOS pipeline."
        ),
    }
    (WEB / "form8k.json").write_text(json.dumps(_stamp(payload), indent=2, default=str))
    print(
        f"[export-terminal] form8k: {payload['total']} events, "
        f"as_of {payload['as_of']}, unclassified {payload['unclassified']}",
        flush=True,
    )


def export_form_ipo() -> None:
    """US IPO registration/pricing stream — EDGAR S-1 family + 424B4 (display-only).

    Reads ``data/cache/form_ipo_aggregate.parquet`` (gitignored; produced by
    ``scripts/form_ipo_fetch.py`` — whole-market EFTS form-level queries over a
    fixed ~120-day window). Status is derived from the immutable form type:
    S-1/S-1/A = ``filed`` (registration on file), 424B4 = ``priced`` (statutory
    final prospectus = pricing complete). Offer price / proceeds / listing date
    live inside the prospectus documents and are NOT parsed (honest v1 limit,
    disclosed in the methodology — never fabricated).
    """
    fp = Path("data/cache/form_ipo_aggregate.parquet")
    if not fp.exists():
        print(
            "[export-terminal] SKIP form_ipo: data/cache/form_ipo_aggregate.parquet "
            "not present (tracked JSON retains last-committed value)",
            flush=True,
        )
        return

    df = pd.read_parquet(fp)
    by_status = {
        k: int(v) for k, v in df["status"].value_counts().sort_index().items()
    }
    by_form = {k: int(v) for k, v in df["form"].value_counts().sort_index().items()}
    filings = []
    # Full window export (every filing visible — the /ipo stream reads newest-
    # first with client-side paging); 1200 is a payload-size safety cap only.
    for _, r in df.head(1200).iterrows():
        filings.append({
            "company": str(r["company"]),
            "ticker": str(r["ticker"]),
            "filed_date": str(r["filed_date"]),
            "form": str(r["form"]),
            "status": str(r["status"]),
            "doc_url": str(r["doc_url"]),
        })
    payload = {
        "status": "ok",
        "as_of": str(df["filed_date"].max()),
        "window": {"start": str(df["filed_date"].min()), "end": str(df["filed_date"].max())},
        "issuers": int(df["issuer_cik"].nunique()),
        "total": int(len(df)),
        "by_status": by_status,
        "by_form": by_form,
        "filings": filings,
        "methodology": (
            "US IPO registration/pricing stream — SEC EDGAR EFTS whole-market "
            "form-level queries (public domain, 17 U.S.C. §105), fixed ~120-day "
            "window, filed-date point-in-time, one row per accession (an S-1/A "
            "amendment is a new filing, never a silent overwrite). Status is "
            "derived from the immutable form type: S-1 / S-1/A = filed "
            "(registration statement on file); 424B4 = priced (the statutory "
            "final prospectus under Securities Act Rule 424(b)(4) is filed "
            "after pricing — its appearance marks a priced offering). Honest "
            "v1 limits, disclosed not papered over: (1) the offer price, share "
            "count, proceeds, and expected listing date live INSIDE the "
            "prospectus documents and are not extracted here — each row links "
            "the filing's EDGAR index page, which lists every document; (2) the "
            "424B4 form-level catch includes priced follow-on offerings by "
            "already-listed issuers (e.g. S-3 shelf takedowns), not only "
            "first-day IPOs — this panel is the registration/pricing STREAM, "
            "not a curated IPO list; (3) a 424B4 whose issuer also filed an S-1 "
            "family document in the window is the classic register-then-price "
            "path, but no company-level state machine is applied (rows are "
            "filing-level). Ticker is parsed from the EDGAR display name where "
            "present; pre-symbol S-1 filers carry none (empty, never guessed). "
            "Counts are FILING counts, not company counts. Display-only, "
            "exploratory, not a research claim; NOT part of any OOS pipeline."
        ),
    }
    (WEB / "ipo.json").write_text(json.dumps(_stamp(payload), indent=2, default=str))
    print(
        f"[export-terminal] form_ipo: {payload['total']} filings "
        f"({payload['by_status']}), {payload['issuers']} issuers, "
        f"as_of {payload['as_of']}",
        flush=True,
    )


def export_form_d() -> None:
    """US Form D exempt-offering stream — the primary-market (一级市场) panel.

    Reads ``data/cache/form_d_aggregate.parquet`` (gitignored; produced by
    ``scripts/form_d_fetch.py`` — whole-market EFTS form-level query,
    ``forms=D`` expands to D + D/A, fixed ~90-day window). Status from the
    immutable form type: D = ``new`` (a new exempt-offering notice),
    D/A = ``amendment`` (new accession). The offering amount / sold amount /
    industry live inside the filing's primary XML and are NOT parsed (honest
    v1 limit, disclosed — resolving one primary doc per filing would cost
    ~4,300 extra requests for the window). Filers are private companies by
    definition: ``ticker`` is almost always empty (honest, never guessed).
    """
    fp = Path("data/cache/form_d_aggregate.parquet")
    if not fp.exists():
        print(
            "[export-terminal] SKIP form_d: data/cache/form_d_aggregate.parquet "
            "not present (tracked JSON retains last-committed value)",
            flush=True,
        )
        return

    df = pd.read_parquet(fp)
    if df.empty:
        print(
            "[export-terminal] SKIP form_d: empty parquet (tracked JSON "
            "retains last-committed value)",
            flush=True,
        )
        return
    by_form = {k: int(v) for k, v in df["form"].value_counts().sort_index().items()}
    # ~145 notices/day → ~4,300/window; visible rows capped for payload size
    # (the stream reads newest-first with client-side paging).
    filings = []
    for _, r in df.head(600).iterrows():
        filings.append({
            "company": str(r["company"]),
            "ticker": str(r["ticker"]),
            "filed_date": str(r["filed_date"]),
            "form": str(r["form"]),
            "status": str(r["status"]),
            "doc_url": str(r["doc_url"]),
        })
    payload = {
        "status": "ok",
        "as_of": str(df["filed_date"].max()),
        "window": {"start": str(df["filed_date"].min()), "end": str(df["filed_date"].max())},
        "issuers": int(df["issuer_cik"].nunique()),
        "total": int(len(df)),
        "by_form": by_form,
        "filings": filings,
        "methodology": (
            "US Form D exempt-offering notices (一级市场) — SEC EDGAR EFTS "
            "whole-market form-level queries (public domain, 17 U.S.C. §105), "
            "fixed ~90-day window, filed-date point-in-time, one row per "
            "accession (a D/A amendment is a new filing, never a silent "
            "overwrite). forms=D expands to D + D/A (live-probed 2026-08-23; "
            "volume ~145 notices/day). Status from the immutable form type: "
            "D = new exempt-offering notice; D/A = amendment. Honest v1 "
            "limits, disclosed not papered over: (1) the offering amount, "
            "amount sold, industry, and related persons live INSIDE the "
            "filing's primary XML document and are not extracted here — each "
            "row links the filing's EDGAR index page, which lists every "
            "document; (2) Form D filers are typically private companies, so "
            "the ticker column is almost always empty (the EDGAR display "
            "name carries none) — honest, never guessed; (3) Form D covers "
            "Regulation D and other exemptions, including hedge-fund and "
            "fund notices — this panel is the exempt-offering STREAM, not a "
            "curated venture-round list; (4) EFTS serves at most 10,000 hits "
            "per query — the first 90-day probe (2026-08-23) hit the cap and "
            "received only the newest 41 days, so the fetch now queries a "
            "rolling 30-day window (~7,300 filings, under the cap) and the "
            "aggregate ACCUMULATES across runs (dedup by accession; the "
            "panel's window spans everything ever fetched). Visible rows "
            "capped at 600 newest for payload size (total/by_form count the "
            "full aggregate). Display-only, exploratory, NOT a research "
            "claim."
        ),
    }
    (WEB / "form_d.json").write_text(json.dumps(_stamp(payload), indent=2, default=str))
    print(
        f"[export-terminal] form_d: {payload['total']} filings "
        f"({payload['by_form']}), {payload['issuers']} issuers, "
        f"as_of {payload['as_of']}",
        flush=True,
    )


def export_filing_stream() -> None:
    """Unified cross-form SEC filing stream (display-only, DERIVED).

    Merges the committed per-form panels — insider 4, event 8-K, IPO S-1
    family + 424B4, exempt D/D/A, activist SC 13D (smart_money), passive
    SC 13G (stakes_13g) — into ONE newest-first feed (the unified-stream
    cluster xiaoyinsi serves). Zero new fetches: every row keeps its source
    panel's own provenance and EDGAR link; per-source visible caps inherit
    (form4 200 / form_d 600 / …) and are disclosed per form in by_form,
    which counts the merged stream, not the EDGAR universe. 13F-HR is
    excluded v1 (quarterly manager filings, not company events — the
    /institutions registry already carries it).
    """
    rows: list[dict] = []

    def add(form: str, who: str, ticker: str, d: str, url: str) -> None:
        # A stream row needs a subject; rows without any who are dropped at
        # the source (never a "—" placeholder row in the feed). smart_money
        # predates https on its links — normalize to the canonical scheme.
        if url.startswith("http://www.sec.gov"):
            url = "https" + url[len("http"):]
        if d and url and who and who != "—":
            rows.append({
                "form": form,
                "who": who,
                # None-coalesce: source panels carry JSON nulls for unknown
                # tickers (never str(None) leaks).
                "ticker": ticker if isinstance(ticker, str) and ticker not in ("", "None") else "",
                "filed_date": d,
                "doc_url": url,
            })

    f4 = _dh_read("form4.json")
    if isinstance(f4, dict) and f4.get("status") == "ok":
        for r in f4.get("recent", []):
            add("4", str(r.get("filer", "")), str(r.get("ticker", "")),
                str(r.get("date", "")), str(r.get("doc_url", "")))
    f8 = _dh_read("form8k.json")
    if isinstance(f8, dict) and f8.get("status") == "ok":
        for r in f8.get("events", []):
            add(str(r.get("form", "8-K")), str(r.get("company", "")),
                str(r.get("ticker", "")), str(r.get("filing_date", "")),
                str(r.get("doc_url", "")))
    ipo = _dh_read("ipo.json")
    if isinstance(ipo, dict) and ipo.get("status") == "ok":
        for r in ipo.get("filings", []):
            add(str(r.get("form", "")), str(r.get("company", "")),
                str(r.get("ticker", "")), str(r.get("filed_date", "")),
                str(r.get("doc_url", "")))
    fd = _dh_read("form_d.json")
    if isinstance(fd, dict) and fd.get("status") == "ok":
        for r in fd.get("filings", []):
            add(str(r.get("form", "")), str(r.get("company", "")),
                str(r.get("ticker", "")), str(r.get("filed_date", "")),
                str(r.get("doc_url", "")))
    def stake_who(filer: object, target: object) -> str:
        """'FILER → TARGET'; a placeholder filer degrades to TARGET alone."""
        f = str(filer or "").strip()
        t = str(target or "").strip()
        if not f or "申报人见原文" in f or f == "None":
            return t or "—"
        return f"{f} → {t}" if t else f

    g13 = _dh_read("stakes_13g.json")
    if isinstance(g13, dict) and g13.get("status") == "ok":
        for r in g13.get("filings", []):
            add(str(r.get("form", "")), stake_who(r.get("filer"), r.get("target")),
                str(r.get("ticker") or ""), str(r.get("date", "")),
                str(r.get("doc_url", "")))
    sm = _dh_read("smart_money.json")
    if isinstance(sm, dict) and sm.get("recent_filings"):
        for r in sm.get("recent_filings", []):
            add(str(r.get("form", "SC 13D")), stake_who(r.get("filer"), r.get("target")),
                str(r.get("ticker") or ""), str(r.get("date", "")),
                str(r.get("url", "")))

    if not rows:
        print(
            "[export-terminal] SKIP filing_stream: no source panels ok "
            "(tracked JSON retains last-committed value)",
            flush=True,
        )
        return
    rows.sort(key=lambda r: (r["filed_date"], r["form"]), reverse=True)
    visible = rows[:800]
    by_form: dict[str, int] = {}
    for r in visible:
        by_form[r["form"]] = by_form.get(r["form"], 0) + 1
    payload = {
        "status": "ok",
        "as_of": visible[0]["filed_date"],
        "window": {
            "start": min(r["filed_date"] for r in visible),
            "end": max(r["filed_date"] for r in visible),
        },
        "total_merged": len(rows),
        "n_visible": len(visible),
        "by_form": dict(sorted(by_form.items(), key=lambda kv: -kv[1])),
        "filings": visible,
        "methodology": (
            "Unified cross-form SEC filing stream — DERIVED by merging the "
            "terminal's own committed per-form panels (insider Form 4, event "
            "8-K/A, IPO S-1 family + 424B4, exempt D/D/A, activist SC 13D/A, "
            "passive SC 13G), newest-first. Zero new fetches: every row keeps "
            "its source panel's provenance and EDGAR link. Honest limits: "
            "(1) each source panel's own visible cap is inherited (e.g. Form 4 "
            "200 recent, Form D 600 newest) — by_form counts the MERGED "
            "VISIBLE stream, not the EDGAR universe; (2) 13F-HR is excluded "
            "in v1 (quarterly manager holdings, not company events — carried "
            "by the /institutions registry); (3) source panels refresh "
            "independently, so form mix shifts as panels advance. Display-"
            "only, exploratory, NOT a research claim."
        ),
    }
    (WEB / "filing_stream.json").write_text(
        json.dumps(_stamp(payload), indent=2, default=str)
    )
    print(
        f"[export-terminal] filing_stream: {len(visible)} visible of "
        f"{len(rows)} merged across {len(by_form)} forms, "
        f"as_of {payload['as_of']}",
        flush=True,
    )


def export_politician_trades() -> None:
    """STOCK Act congressional trading — House PTR filing stream (display-only).

    Reads ``data/cache/politician_trades_aggregate.parquet`` (gitignored;
    produced by ``scripts/politician_trades_fetch.py`` — House Clerk PTR
    index, filing-stream level: member / office / filing type / year / PDF
    link). Transaction detail (assets, amounts, dates) lives inside the
    source PDFs and is NOT parsed; late-filing days cannot be computed at
    list level. Senate eFD is Akamai-blocked and disclosed as such.
    """
    fp = Path("data/cache/politician_trades_aggregate.parquet")
    if not fp.exists():
        print(
            "[export-terminal] SKIP politician_trades: data/cache/"
            "politician_trades_aggregate.parquet not present (tracked JSON "
            "retains last-committed value)",
            flush=True,
        )
        return

    df = pd.read_parquet(fp)

    # Party join (house.gov current-member directory): office match + LAST-NAME
    # corroboration — candidates/former members whose StateDst names a district
    # they do not hold stay null (never attributed the incumbent's party).
    from aionis.ingest.politician_trades import join_party

    directory_fp = Path("data/cache/house_directory.parquet")
    parties: list[str | None] = [None] * len(df)
    if directory_fp.exists():
        parties = join_party(df, pd.read_parquet(directory_fp))
    df["party"] = parties
    n_party = int(df["party"].notna().sum())

    filings = []
    # Full filing-stream export (visible == total; 874 filings in the current
    # window) — the /congress view pages client-side. 1000 is a payload-size
    # safety cap, not a display truncation.
    for _, r in df.head(1000).iterrows():
        filings.append({
            "member": str(r["member"]),
            "office": str(r["office"]),
            "filing_type": str(r["filing_type"]),
            "filing_date": str(r["filing_date"]) if pd.notna(r["filing_date"]) else None,
            "filing_year": int(r["filing_year"]),
            "party": r["party"] if pd.notna(r["party"]) else None,
            "doc_url": str(r["doc_url"]),
        })
    top_members = [
        {"member": str(m), "office": str(o), "count": int(c)}
        for (m, o), c in df.groupby(["member", "office"]).size()
        .sort_values(ascending=False)
        .head(12)
        .items()
    ]
    by_year = {str(y): int(n) for y, n in df["filing_year"].value_counts().sort_index().items()}
    payload = {
        "status": "ok",
        # Real filed dates from the bulk FD.xml index (M/D/YYYY as filed,
        # normalized); null only if the index carried none.
        "as_of": str(df["filing_date"].dropna().max()) if df["filing_date"].notna().any() else None,
        "latest_filing_year": int(df["filing_year"].max()),
        "window_years": sorted(int(y) for y in df["filing_year"].unique()),
        "house": {
            "total": int(len(df)),
            "members": int(df["member"].nunique()),
            "filings": filings,
            "by_year": by_year,
            "top_members": top_members,
            "party_coverage": f"{n_party}/{len(df)}",
        },
        "senate": {
            "status": "blocked",
            "note": "efdsearch.senate.gov serves Akamai 'Access Denied' to plain GET — no first-party access; disclosed rather than routed through third parties.",
        },
        "methodology": (
            "STOCK Act congressional trading, v1 = U.S. House Clerk PTR "
            "(Periodic Transaction Report) FILING-STREAM index — public "
            "domain. Source: the Clerk's daily bulk index "
            "(financial-pdfs/{year}FD.zip -> FD.xml), one polite request per "
            "year; FilingType 'P' rows are PTRs with the member, state-"
            "district office, and the as-filed FilingDate; each row links the "
            "source PDF by DocID. Transaction detail (asset, amount band, "
            "trade dates — the basis of the 45-day late-filing rule) lives "
            "inside those PDFs and is NOT parsed; this panel therefore shows "
            "WHO filed WHEN, never what was traded — no amounts or tickers "
            "are fabricated. The Senate eFD source is Akamai-blocked "
            "(disclosed as blocked, not circumvented through third-party "
            "APIs whose licenses fail the 7-gate). Party labels come from the "
            "house.gov current-member directory joined on district + last "
            "name (office-only, no name corroboration → null; candidates and "
            "former members never inherit the incumbent's party). Window "
            "2025-2026. Display-only, not a research claim; NOT part of "
            "any OOS pipeline."
        ),
    }
    (WEB / "politician_trades.json").write_text(
        json.dumps(_stamp(payload), indent=2, default=str)
    )
    print(
        f"[export-terminal] politician_trades: {payload['house']['total']} filings, "
        f"{payload['house']['members']} members, "
        f"years {payload['window_years']}",
        flush=True,
    )


def export_politician_trades_tx() -> None:
    """STOCK Act — House PTR TRANSACTION-level panel (display-only).

    Reads ``data/cache/politician_trades_tx.parquet`` (+ ``_stats.json``;
    gitignored, produced by ``scripts/politician_trades_tx_fetch.py`` — the
    revived salvage parser: per-PDF transaction rows with ticker / asset /
    direction / statutory $ band / dates, plus the honest reconciliation
    counters). Party join reuses the filing-stream panel's district+last-name
    double corroboration (``join_party`` — candidates/former members stay
    null). The filing-stream panel above is untouched; this is the
    transaction-granularity companion (owner D4 gate).
    """
    fp = Path("data/cache/politician_trades_tx.parquet")
    stats_fp = Path("data/cache/politician_trades_tx_stats.json")
    if not fp.exists() or not stats_fp.exists():
        print(
            "[export-terminal] SKIP politician_trades_tx: data/cache/"
            "politician_trades_tx{.parquet,_stats.json} not present (tracked "
            "JSON retains last-committed value)",
            flush=True,
        )
        return

    df = pd.read_parquet(fp)
    stats = json.loads(stats_fp.read_text(encoding="utf-8"))
    if df.empty:
        print(
            "[export-terminal] SKIP politician_trades_tx: empty parquet "
            "(tracked JSON retains last-committed value)",
            flush=True,
        )
        return

    from aionis.ingest.politician_trades import join_party

    directory_fp = Path("data/cache/house_directory.parquet")
    parties: list[str | None] = [None] * len(df)
    if directory_fp.exists():
        parties = join_party(df, pd.read_parquet(directory_fp))
    df["party"] = parties
    n_party = int(df["party"].notna().sum())

    # Full export (visible == total; cap is a payload-size safety net only).
    transactions = []
    for _, r in df.head(5000).iterrows():
        transactions.append({
            "member": str(r["member"]),
            "party": r["party"] if pd.notna(r["party"]) else None,
            "office": str(r["office"]),
            "ticker": str(r["ticker"]),
            "asset": str(r["asset"]),
            "type": str(r["asset_class"]),
            "direction": str(r["direction"]),
            "amount_range": str(r["amount_range"]),
            "transaction_date": str(r["transaction_date"].date()),
            "filing_date": str(r["filing_date"].date())
            if pd.notna(r["filing_date"]) else None,
            "days_late": int(r["days_late"]) if pd.notna(r["days_late"]) else None,
            "doc_url": str(r["doc_url"]),
        })

    by_party: dict[str, dict[str, int]] = {}
    for party_key, g in df.groupby(df["party"].fillna("unknown")):
        by_party[str(party_key)] = {
            "n_trades": int(len(g)),
            "n_buy": int((g["direction"] == "buy").sum()),
            "n_sell_partial": int((g["direction"] == "sell_partial").sum()),
            "n_sell_full": int((g["direction"] == "sell_full").sum()),
        }

    payload = {
        "status": "ok",
        # Latest as-filed FilingDate among the filings the rows came from.
        "as_of": str(df["filing_date"].dropna().max())
        if df["filing_date"].notna().any() else None,
        "year": int(stats.get("year", df["filing_year"].max())),
        "total": int(len(df)),
        "n_members": int(df["member"].nunique()),
        "n_tickered": int((df["ticker"] != "").sum()),
        "by_party": by_party,
        # STOCK Act 45-day clock, per transaction (filing - transacted).
        "late_filings": int((df["days_late"] > 45).sum()),
        "party_coverage": f"{n_party}/{len(df)}",
        "transactions": transactions,
        # Honest parsing reconciliation — never silently dropped rows.
        "parse": {
            "filings_total": int(stats.get("filings_total", 0)),
            "filings_processed": int(stats.get("filings_processed", 0)),
            "fetch_errors": int(len(stats.get("fetch_errors", []))),
            "no_text_pdfs": int(len(stats.get("no_text_pdfs", []))),
            "row_candidates": int(stats.get("row_candidates", 0)),
            "rows_parsed": int(stats.get("rows_parsed", 0)),
            "rows_exchanged": int(stats.get("rows_excluded", 0)),
            "parse_failures": int(
                stats.get("row_candidates", 0)
                - stats.get("rows_parsed", 0)
                - stats.get("rows_excluded", 0)
            ),
            "complete": bool(stats.get("complete", False)),
        },
        "senate": {
            "status": "blocked",
            "note": "efdsearch.senate.gov serves Akamai 'Access Denied' to plain GET — no first-party access; disclosed rather than routed through third parties.",
        },
        "methodology": (
            "STOCK Act congressional trading, v2 = TRANSACTION level. Source: "
            "the same U.S. House Clerk public-domain filings as the filing-"
            "stream panel, with the PTR PDFs themselves parsed (RC4-decrypted "
            "with the Python standard library; no third-party data). Each row "
            "is one transaction as filed: member, ticker (when the PDF "
            "carries one), asset description, buy vs sell (partial/full), the "
            "STATUTORY DISCLOSURE BAND (not an exact amount), transaction "
            "date, and filing date; days_late = filing - transacted against "
            "the 45-day STOCK Act clock. Parsing is disclosed, never silent: "
            "row_candidates counts every type+dates+amount anchor found; "
            "non-purchase/sale types (e.g. exchanges) are excluded and "
            "counted; parse_failures = candidates - rows - exchanges; "
            "no-text (scanned) PDFs are counted separately; an asset "
            "description may retain a brokerage annotation on wrapped rows. "
            "Party labels reuse the house.gov directory join (district + "
            "last name; candidates/former members stay null). Senate eFD is "
            "Akamai-blocked and disclosed. House-only, 2026 filings to date. "
            "Display-only, not a research claim; NOT part of any OOS "
            "pipeline."
        ),
    }
    (WEB / "politician_trades_tx.json").write_text(
        json.dumps(_stamp(payload), indent=2, default=str)
    )
    print(
        f"[export-terminal] politician_trades_tx: {payload['total']} transactions, "
        f"{payload['n_members']} members, late>45d {payload['late_filings']}, "
        f"parse failures {payload['parse']['parse_failures']}, as_of {payload['as_of']}",
        flush=True,
    )


def export_party_index() -> None:
    """Party opposition index + party follow portfolios (display-only).

    DERIVED panel: reads the committed ``politician_trades_tx.json`` payload
    written by ``export_politician_trades_tx`` (never the gitignored cache
    parquet) and aggregates it — zero new fetches. Per calendar month, for
    every ticker BOTH House parties traded, net direction (buys − sells) per
    party; the OPPOSITION share = fraction of both-directional common tickers
    signed opposite (D net-buy while R net-sell, or vice versa). The follow
    portfolios are the trailing 90-day top net-buy books per party — count-
    weighted SIGNAL lists only (the PTR carries statutory $ bands, not exact
    amounts, so dollar-weighting would be a lie): no prices, no returns, no
    performance claim. Display lane, never a research signal.
    """
    src = _dh_read("politician_trades_tx.json")
    if not isinstance(src, dict) or src.get("status") != "ok":
        print(
            "[export-terminal] SKIP party_index: politician_trades_tx.json "
            "not present or not ok (tracked JSON retains last-committed value)",
            flush=True,
        )
        return
    tx = [
        r
        for r in src.get("transactions", [])
        if r.get("ticker") and r.get("party") in ("D", "R")
    ]
    if not tx:
        print(
            "[export-terminal] SKIP party_index: no tickered D/R transactions "
            "in the source panel (tracked JSON retains last-committed value)",
            flush=True,
        )
        return

    # ---- Monthly opposition series -------------------------------------
    months: dict[str, dict[str, dict]] = {}
    for r in tx:
        b = months.setdefault(r["transaction_date"][:7], {"D": {}, "R": {}})
        t = b[r["party"]].setdefault(r["ticker"], {"buy": 0, "sell": 0})
        t["buy" if r["direction"] == "buy" else "sell"] += 1

    month_rows: list[dict] = []
    detail: dict[str, list] = {}
    for m in sorted(months):
        dmap, rmap = months[m]["D"], months[m]["R"]
        common = sorted(set(dmap) & set(rmap))
        directional: list[dict] = []
        for tkr in common:
            d_net = dmap[tkr]["buy"] - dmap[tkr]["sell"]
            r_net = rmap[tkr]["buy"] - rmap[tkr]["sell"]
            if d_net == 0 or r_net == 0:
                continue
            row = {
                "ticker": tkr,
                "d_net": d_net,
                "r_net": r_net,
                "n_d": dmap[tkr]["buy"] + dmap[tkr]["sell"],
                "n_r": rmap[tkr]["buy"] + rmap[tkr]["sell"],
            }
            directional.append(row)
        opposed = [d for d in directional if (d["d_net"] > 0) != (d["r_net"] > 0)]
        month_rows.append({
            "month": m,
            "d_tx": sum(v["buy"] + v["sell"] for v in dmap.values()),
            "r_tx": sum(v["buy"] + v["sell"] for v in rmap.values()),
            "d_buy": sum(v["buy"] for v in dmap.values()),
            "r_buy": sum(v["buy"] for v in rmap.values()),
            "n_common": len(common),
            "n_directional": len(directional),
            "n_opposed": len(opposed),
            "opposition": round(len(opposed) / len(directional), 4) if directional else None,
        })
        detail[m] = sorted(
            directional, key=lambda d: (-(d["n_d"] + d["n_r"]), d["ticker"])
        )

    # Headline month = latest WITH both-directional common tickers (a sparse
    # current month honestly yields no opposition; the series still shows it
    # as null rather than dropping it).
    latest_month = next(
        (r for r in reversed(month_rows) if r["opposition"] is not None),
        month_rows[-1],
    )
    latest_detail = detail[latest_month["month"]]
    opposed_rows = [
        d for d in latest_detail if (d["d_net"] > 0) != (d["r_net"] > 0)
    ][:10]
    consensus_rows = [d for d in latest_detail if d["d_net"] > 0 and d["r_net"] > 0][:10]

    # ---- Trailing-90d follow portfolios --------------------------------
    from datetime import date, timedelta

    max_tx = max(r["transaction_date"] for r in tx)
    cutoff = (date.fromisoformat(max_tx) - timedelta(days=90)).isoformat()
    window = [r for r in tx if r["transaction_date"] >= cutoff]

    portfolios: dict[str, dict] = {}
    for p in ("D", "R"):
        rows = [r for r in window if r["party"] == p]
        agg: dict[str, dict] = {}
        for r in rows:
            a = agg.setdefault(
                r["ticker"], {"buy": 0, "sell": 0, "members": set(), "assets": {}}
            )
            a["buy" if r["direction"] == "buy" else "sell"] += 1
            a["members"].add(r["member"])
            if r.get("asset"):
                a["assets"][r["asset"]] = a["assets"].get(r["asset"], 0) + 1
        holdings = sorted(
            (
                {
                    "ticker": tkr,
                    "asset": max(a["assets"], key=a["assets"].get) if a["assets"] else "",
                    "n_buy": a["buy"],
                    "n_sell": a["sell"],
                    "net_buy": a["buy"] - a["sell"],
                    "n_members": len(a["members"]),
                }
                for tkr, a in agg.items()
            ),
            key=lambda h: (-h["net_buy"], -h["n_buy"], h["ticker"]),
        )[:10]
        portfolios[p] = {
            "n_tx": len(rows),
            "n_members": len({r["member"] for r in rows}),
            "holdings": holdings,
        }

    payload = {
        "status": "ok",
        "as_of": src.get("as_of"),
        "source_panel": "politician_trades_tx",
        # Latest transaction_date feeding the panel (window anchor).
        "window_anchor": max_tx,
        "window_days": 90,
        "n_source_tx": len(tx),
        "months": month_rows,
        "latest": {
            "month": latest_month["month"],
            "opposition": latest_month["opposition"],
            "opposed": opposed_rows,
            "consensus": consensus_rows,
        },
        "portfolios": portfolios,
        "methodology": (
            "Party opposition index + follow portfolios, DERIVED from the "
            "committed politician_trades_tx panel (House-only 2026 PTR PDF "
            "parses; zero new fetches). Opposition: per calendar month, for "
            "every ticker BOTH parties traded, net direction = buys − sells "
            "(count-weighted; the PTR discloses statutory $ bands, not exact "
            "amounts, so dollar-weighting would be fabricated precision); "
            "the index = share of both-directional common tickers signed "
            "opposite (D net-buy vs R net-sell or vice versa); null when no "
            "ticker carries both parties' net direction that month. Follow "
            "portfolios: trailing 90 days from the latest transaction date, "
            "top-10 tickers per party by net buy count — SIGNAL LISTS ONLY, "
            "no prices, no returns, no performance claim (display lane; live "
            "prices are display-only and never enter any pipeline). "
            "Unknown-party and un-tickered rows are excluded from the math "
            "and remain visible in the source panel."
        ),
    }
    (WEB / "party_index.json").write_text(
        json.dumps(_stamp(payload), indent=2, default=str)
    )
    print(
        f"[export-terminal] party_index: {len(month_rows)} months, latest "
        f"{latest_month['month']} opposition "
        f"{latest_month['opposition'] if latest_month['opposition'] is not None else 'n/a'} "
        f"({latest_month['n_opposed']}/{latest_month['n_directional']} directional), "
        f"portfolios D {portfolios['D']['n_tx']}tx / R {portfolios['R']['n_tx']}tx "
        f"since {cutoff}",
        flush=True,
    )


def export_ark() -> None:
    """ARK Invest 8-ETF daily holdings — official CSVs (display-only).

    Reads the LATEST cached snapshot per fund from
    ``data/cache/ark_holdings/`` (gitignored; written by
    ``scripts/ark_holdings_fetch.py`` via ``aionis.ingest.ark_holdings`` —
    the exporter reuses that parser so cache and JSON can never disagree on
    row semantics). Top-10 per fund by weight + a family-overlap view
    (tickers held by ≥2 ARK funds — the "what does the whole family like"
    cut xiaoyinsi's institutions cluster carries). ARK keeps no CSV history:
    the dated cache snapshots ARE the time series; no prices, no returns,
    no performance claim. Display lane only.
    """
    cache = Path("data/cache/ark_holdings")
    csvs = sorted(cache.glob("*_*.csv")) if cache.exists() else []
    if not csvs:
        print(
            "[export-terminal] SKIP ark: data/cache/ark_holdings/ has no "
            "snapshots (tracked JSON retains last-committed value)",
            flush=True,
        )
        return

    from aionis.ingest.ark_holdings import FUND_CSV_URLS, parse_csv

    latest: dict[str, tuple[str, Path]] = {}
    for fp in csvs:
        m = re.fullmatch(r"([A-Z]+)_(\d{8})\.csv", fp.name)
        if not m:
            continue
        tick, ymd = m.group(1), m.group(2)
        if tick not in FUND_CSV_URLS or tick not in latest or ymd > latest[tick][0]:
            latest[tick] = (ymd, fp)

    funds: list[dict] = []
    overlap: dict[str, dict] = {}
    for tick in FUND_CSV_URLS:
        if tick not in latest:
            continue  # a fund's fetch failed once — omitted, never guessed
        ymd, fp = latest[tick]
        as_of, rows, skipped = parse_csv(fp.read_text(encoding="utf-8"))
        rows = sorted(rows, key=lambda r: (-r["weight_pct"], r["ticker"]))
        funds.append({
            "ticker": tick,
            "fund": rows[0]["fund"] if rows else "",
            "as_of": as_of,
            "n_positions": len(rows),
            "skipped_rows": skipped,
            "top": [
                {
                    "ticker": r["ticker"],
                    "company": r["company"],
                    "weight_pct": r["weight_pct"],
                    "market_value": r["market_value"],
                }
                for r in rows[:10]
            ],
        })
        for r in rows:
            o = overlap.setdefault(r["ticker"], {"ticker": r["ticker"], "company": r["company"], "funds": [], "max_weight_pct": 0.0})
            o["funds"].append(tick)
            o["max_weight_pct"] = max(o["max_weight_pct"], r["weight_pct"])

    if not funds:
        print(
            "[export-terminal] SKIP ark: no parseable snapshots (tracked "
            "JSON retains last-committed value)",
            flush=True,
        )
        return
    shared = sorted(
        (o for o in overlap.values() if len(o["funds"]) >= 2),
        key=lambda o: (-len(o["funds"]), -o["max_weight_pct"], o["ticker"]),
    )[:20]

    payload = {
        "status": "ok",
        "as_of": max(f["as_of"] for f in funds),
        "n_funds": len(funds),
        "n_funds_expected": len(FUND_CSV_URLS),
        "funds": funds,
        "family_overlap": shared,
        "methodology": (
            "ARK Invest daily fund holdings, from ARK's own official Full "
            "Holdings CSVs on assets.ark-funds.com (free, public, published "
            "each trading day after close). The eight endpoint URLs were "
            "extracted once via browser from each fund page's live DOM "
            "(2026-08-23) — the fund pages are a JS shell with no href in "
            "raw HTML; a fund rename surfaces as an honest per-fund failure, "
            "never a silent gap. Rows: official weight/market value as "
            "published; skipped rows are counted and disclosed (the trailing "
            "disclaimer footer, warrant/unit rows with no ticker, CASHX "
            "cash rows). Top-10 per fund by weight; family overlap lists "
            "tickers held by 2+ ARK funds. ARK keeps no CSV history — the "
            "dated local snapshots are the only time series. Display-only, "
            "exploratory; no prices, no returns, no performance claim; NOT "
            "part of any research or OOS pipeline."
        ),
    }
    (WEB / "ark.json").write_text(
        json.dumps(_stamp(payload), indent=2, default=str)
    )
    print(
        f"[export-terminal] ark: {payload['n_funds']}/{payload['n_funds_expected']} "
        f"funds, {sum(f['n_positions'] for f in funds)} positions, "
        f"{len(shared)} family-overlap tickers, as_of {payload['as_of']}",
        flush=True,
    )


def export_reddit_trending() -> None:
    """ApeWisdom Reddit trending-stocks board (free public API; display-only).

    Reads ``data/cache/ape_wisdom_stocks.json`` (gitignored; written by
    ``scripts/ape_wisdom_fetch.py`` via ``aionis.ingest.ape_wisdom`` — the
    domain is apewisdom.io, no key, verified live 2026-08-23). First-party
    ranking fields stored verbatim (rank/ticker/name/mentions/upvotes/
    rank_24h_ago/mentions_24h_ago). The free API's pagination is DEAD as of
    verification day: the envelope declares 3 pages/290 tickers but serves
    page 1 only (100 rows) for every pagination form — the ingest trusts the
    envelope's own ``current_page`` echo, records served_pages/pagination_ok,
    and the panel discloses "visible = first 100 of a declared 290" rather
    than padding. A TODAY snapshot by definition (ApeWisdom keeps no
    history); the display lane's own Reddit collector panel is untouched.
    """
    fp = Path("data/cache/ape_wisdom_stocks.json")
    if not fp.exists():
        print(
            "[export-terminal] SKIP reddit_trending: data/cache/"
            "ape_wisdom_stocks.json not present (tracked JSON retains "
            "last-committed value)",
            flush=True,
        )
        return
    cache = json.loads(fp.read_text(encoding="utf-8"))
    rows = cache.get("rows") or []
    if not rows:
        print(
            "[export-terminal] SKIP reddit_trending: empty cache (tracked "
            "JSON retains last-committed value)",
            flush=True,
        )
        return

    tickers = [
        {
            "rank": int(r["rank"]),
            "ticker": str(r["ticker"]),
            "name": str(r.get("name") or ""),
            "mentions": int(r.get("mentions") or 0),
            "upvotes": int(r.get("upvotes") or 0),
            # First-party nullable 24h lags (null = unranked/unmentioned).
            "rank_24h_ago": int(r["rank_24h_ago"]) if r.get("rank_24h_ago") is not None else None,
            "mentions_24h_ago": (
                int(r["mentions_24h_ago"]) if r.get("mentions_24h_ago") is not None else None
            ),
        }
        for r in rows
        if r.get("ticker")
    ]
    # The ingest already dedupes exact (rank, ticker) pairs across pages; a
    # final stable sort by rank presents the coherent board.
    tickers.sort(key=lambda r: r["rank"])

    payload = {
        "status": "ok",
        "as_of": cache.get("fetched_at"),
        "source": "ApeWisdom (apewisdom.io) free public API — filter/stocks",
        "count_declared": int(cache.get("count") or 0),
        "n_rows": len(tickers),
        "served_pages": int(cache.get("served_pages") or 1),
        "pagination_ok": bool(cache.get("pagination_ok", True)),
        # Sibling filters' honest empty envelopes (coverage disclosure, not a
        # swap): all_posts/crypto returned count=0 on 2026-08-23.
        "sibling_filters": cache.get("probe") or {},
        "tickers": tickers,
        "methodology": (
            "Reddit trending-stocks board from ApeWisdom's free public JSON "
            "API (apewisdom.io — the .com domain does not connect; verified "
            "live via browser 2026-08-23, no key, no auth). ApeWisdom "
            "aggregates ticker mentions across subreddits (wallstreetbets & "
            "friends) and is the source xiaoyinsi's own /reddit board "
            "discloses. Fields are first-party and stored verbatim: rank, "
            "ticker, name, mentions, upvotes, and the 24h-ago rank/mentions "
            "lags (null = unranked then). Only the filter/stocks endpoint "
            "carried data on verification day — all-posts and crypto "
            "returned honest zero envelopes, recorded in sibling_filters. "
            "The free API's pagination is dead as of 2026-08-23: the "
            "envelope declares 3 pages/290 tickers but serves page 1 only "
            "(100 rows) for every pagination form (?page=N and path /N — "
            "browser-verified); the ingest trusts the envelope's own "
            "current_page echo and the board shows the honest first 100 of "
            "a declared 290, never padded. TODAY "
            "snapshot only: ApeWisdom keeps no history, so this panel is "
            "never PIT and never a research signal. Politeness: >=2s "
            "between page GETs. Display-only, NOT part of any research or "
            "OOS pipeline."
        ),
    }
    (WEB / "reddit_trending.json").write_text(
        json.dumps(_stamp(payload), indent=2, default=str)
    )
    top = tickers[0]
    print(
        f"[export-terminal] reddit_trending: {payload['n_rows']} tickers "
        f"(declared {payload['count_declared']}), top {top['ticker']} "
        f"{top['mentions']} mentions, as_of {payload['as_of']}",
        flush=True,
    )


def export_executives() -> None:
    """Officer/director-change filings — 8-K Item 5.02 stream (display-only).

    DERIVED panel: reads the ``form8k.json`` payload written by
    ``export_form8k`` (never the gitignored cache parquet) and filters the
    ``officer_changes`` category — 8-K Item 5.02 (officer departures/
    appointments, director elections). Filing-stream level BY DESIGN: one row
    per accession with company / filing date / full item list / EDGAR primary-
    doc link. Person-level extraction (names, roles, appointed-vs-departed
    direction) from 8-K free text is unreliable and is DEFERRED — an honest
    omission beats a guessed name (same v1 boundary as /congress PTR).
    """
    f8 = _dh_read("form8k.json")
    if not isinstance(f8, dict) or f8.get("status") != "ok":
        print(
            "[export-terminal] SKIP executives: form8k.json not present or not "
            "ok (tracked JSON retains last-committed value)",
            flush=True,
        )
        return

    events = [
        {
            "company": str(e["company"]),
            "ticker": str(e["ticker"]),
            "filing_date": str(e["filing_date"]),
            "items": [i for i in e.get("items", [])],
            "doc_url": str(e["doc_url"]),
        }
        for e in f8.get("events", [])
        if e.get("category") == "officer_changes"
    ]
    by_company: dict[str, int] = {}
    for e in events:
        by_company[e["company"]] = by_company.get(e["company"], 0) + 1
    # Count-desc then name — deterministic pill order for the view.
    by_company = dict(sorted(by_company.items(), key=lambda kv: (-kv[1], kv[0])))
    dates = [e["filing_date"] for e in events]
    payload = {
        "status": "ok",
        "as_of": max(dates) if dates else None,
        "total": len(events),
        "issuers": len({e["ticker"] for e in events}),
        "window": {
            "start": min(dates) if dates else None,
            "end": max(dates) if dates else None,
        },
        "events": events,
        "by_company": by_company,
        "methodology": (
            "SEC Form 8-K Item 5.02 officer/director-change filings — DERIVED "
            "from the committed form8k panel (category 'officer_changes'; "
            "public domain, 17 U.S.C. §105, filed-date PIT). v1 is "
            "FILING-STREAM level: one row per 8-K accession with the company, "
            "filing date, full item list and EDGAR primary-document link. "
            "Person-level extraction (who, which role, appointed vs departed) "
            "is DEFERRED: parsing names from 8-K free text is unreliable and "
            "an honest omission beats a guessed name — the same v1 boundary "
            "as the /congress PTR panel. Inherits the /events panel's "
            "bounded 5-issuer universe and 2026-05 window. Display-only, "
            "exploratory, not a research claim; NOT part of any OOS pipeline."
        ),
    }
    (WEB / "executives.json").write_text(json.dumps(_stamp(payload), indent=2))
    print(
        f"[export-terminal] executives: {payload['total']} Item 5.02 filings, "
        f"{payload['issuers']} issuers, as_of {payload['as_of']}",
        flush=True,
    )


def _safe_export(name: str, fn, /, *args, **kwargs):
    """Best-effort guard for the daily CI refresh.

    ``refresh-terminal-data`` runs on a fresh checkout where the gitignored
    research artifacts (``runs/*.parquet`` OOS scores + feature panels and
    ``runs/*.json`` surveys) and some ``data/cache/*.parquet`` caches are absent
    — they regenerate on research cadence, not daily. An exporter whose source is
    missing skips with a log, leaving the tracked ``web/src/data/aionis/*.json``
    at its last committed value. Only ``FileNotFoundError`` is swallowed, so
    genuine bugs still surface. Returns the wrapped call's value, or ``None``.
    """
    try:
        return fn(*args, **kwargs)
    except FileNotFoundError as e:
        print(
            f"[export-terminal] SKIP {name}: {e.filename or e} not present "
            f"(research/cache artifact absent on fresh CI checkout; tracked "
            f"JSON retains last-committed value)",
            flush=True,
        )
        return None


def main() -> None:
    # Daily CI refresh on a fresh checkout lacks the gitignored runs/ research
    # artifacts (OOS scores, panels, surveys) and some data/cache caches. Guard
    # every exporter so a missing source skips (tracked JSON keeps its value)
    # instead of crashing the whole refresh. Only FileNotFoundError is swallowed.
    # Shared payloads (reused from the Quarto exporter, redirected to web/).
    _safe_export("sigma_survey", eq.export_sigma_survey)
    _safe_export("bps_sweep", eq.export_bps_sweep)
    _safe_export("power_floor", eq.export_power_floor)
    _safe_export("evidence", eq.export_evidence)
    _safe_export("ic_monthly", eq.export_ic_monthly)
    # Terminal-specific.
    picks = _safe_export("picks", export_picks)
    if picks is not None:
        latest, n_total = picks
        _safe_export("metrics", export_metrics, latest, n_total)
    _safe_export("sector_breakdown", export_sector_breakdown)
    _safe_export("picks_backtest", export_picks_backtest)
    _safe_export("taco", export_taco)
    _safe_export("pick_conviction", export_pick_conviction)
    _safe_export("themes", export_themes)
    _safe_export("theme_signals", export_theme_signals)
    _safe_export("model_health", export_model_health)
    _safe_export("calibration_reliability", export_calibration_reliability)
    _safe_export("cot", export_cot)
    _safe_export("form4", export_form4)
    _safe_export("form8k", export_form8k)
    _safe_export("form_ipo", export_form_ipo)
    _safe_export("form_d", export_form_d)
    # filing_stream merges the committed panels written above — after them,
    # before the freshness map / catalog that index it.
    _safe_export("filing_stream", export_filing_stream)
    _safe_export("politician_trades", export_politician_trades)
    _safe_export("politician_trades_tx", export_politician_trades_tx)
    # party_index derives from the committed politician_trades_tx.json written
    # just above — keep directly after it, before the freshness map.
    _safe_export("party_index", export_party_index)
    _safe_export("form13f", export_form13f)
    _safe_export("market_context", export_market_context)
    _safe_export("macro_drivers", export_macro_drivers)
    _safe_export("smart_money", export_smart_money)
    _safe_export("stakes_13g", export_stakes13g)
    _safe_export("ark", export_ark)
    _safe_export("reddit_meta", export_reddit_meta)
    _safe_export("reddit_trending", export_reddit_trending)
    _safe_export("ledger_audit", export_ledger_audit)
    _safe_export("headline_provenance", export_headline_provenance)
    # Per-stock view joins the corroboration JSONs above — keep after them.
    _safe_export("stock_universe", export_stock_universe)
    # Executives derives from the committed form8k.json written above — after
    # form8k, before the freshness map / catalog that index it.
    _safe_export("executives", export_executives)
    # Freshness map reads every panel's committed JSON — must run last.
    _safe_export("data_health", export_data_health)
    # API catalog reads data_health — run after it.
    _safe_export("api_catalog", export_api_catalog)
    written = sorted(p.name for p in WEB.glob("*.json"))
    print(f"[export-terminal] wrote {len(written)} files to {WEB}/: {written}", flush=True)


if __name__ == "__main__":
    main()
