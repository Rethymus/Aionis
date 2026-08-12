"""Contract tests for the web terminal's alt-data payloads (web/src/data/aionis/).

These guard the fintech terminal's special-data modules: the JSON files are the
only thing CI renders against (data/cache + runs/ are gitignored), so a silent
change to export_cot/export_form4/export_pick_conviction or to the underlying
fetch must surface here. Pure checks on tracked artifacts — hermetic, no network,
no runs/cache dependency. They also lock the schema the React views depend on
(buy_or_sell enum, z-score sign, etc.).
"""
from __future__ import annotations

import json
from pathlib import Path

DATA = Path("web/src/data/aionis")


def _load(name: str) -> dict:
    return json.loads((DATA / name).read_text())


# --- CFTC COT positioning index ----------------------------------------------


def test_cot_status_and_shape() -> None:
    cot = _load("cot.json")
    assert cot["status"] in {"ok", "awaiting_fetch"}
    assert isinstance(cot["markets"], list)
    assert "composite" in cot and "methodology" in cot


def test_cot_markets_schema_when_ok() -> None:
    cot = _load("cot.json")
    if cot["status"] != "ok":
        return
    assert len(cot["markets"]) >= 4, "COT needs >=4 markets for a meaningful index"
    for m in cot["markets"]:
        assert {"name", "net", "z", "long", "short"} <= set(m)
        assert isinstance(m["name"], str)
        assert isinstance(m["net"], int)
        assert isinstance(m["z"], int | float)
        assert m["long"] >= 0 and m["short"] >= 0
    # markets sorted by z descending (long crowding first) — view relies on order
    zs = [m["z"] for m in cot["markets"]]
    assert zs == sorted(zs, reverse=True)


def test_cot_composite_series_when_ok() -> None:
    cot = _load("cot.json")
    if cot["status"] != "ok":
        return
    series = cot["composite_series"]
    assert len(series) >= 20
    for pt in series:
        assert {"date", "z"} <= set(pt)
        assert isinstance(pt["z"], int | float)
    # Dates must be strictly ascending (time-series invariant).
    dates = [pt["date"] for pt in series]
    assert dates == sorted(dates), "composite_series dates must be ascending"


# --- Form 4 insiders ----------------------------------------------------------


def test_form4_status_and_shape() -> None:
    f = _load("form4.json")
    assert f["status"] in {"ok", "awaiting_fetch"}
    assert isinstance(f["recent"], list)
    assert isinstance(f["top_insiders"], list)


def test_form4_action_enum_when_ok() -> None:
    """Lock the SEC-correct P/S -> buy/sell mapping (regression guard for the
    earlier A/D -> P/S parser fix)."""
    f = _load("form4.json")
    if f["status"] != "ok":
        return
    for r in f["recent"]:
        assert r["action"] in {"buy", "sell"}, f"action must be buy/sell, got {r['action']}"
    # buys/sells are full-window counters (recent is top-50); just sanity-check types.
    assert isinstance(f["buys"], int) and isinstance(f["sells"], int)
    assert f["buys"] >= 0 and f["sells"] >= 0


def test_form4_yearly_breakdown_when_present() -> None:
    """Validate the yearly buy/sell breakdown if present (guarded for stale JSON)."""
    f = _load("form4.json")
    if f["status"] != "ok":
        return
    if "yearly" not in f:
        return  # Stale JSON before re-export
    yearly = f["yearly"]
    assert isinstance(yearly, list)
    if len(yearly) > 0:
        # Years must be ascending integers.
        years = [entry["year"] for entry in yearly]
        assert years == sorted(years), "yearly years must be ascending"
        for entry in yearly:
            assert {"year", "buys", "sells"} <= set(entry)
            assert isinstance(entry["year"], int)
            assert isinstance(entry["buys"], int) and entry["buys"] >= 0
            assert isinstance(entry["sells"], int) and entry["sells"] >= 0
    # Window must be a non-empty string (dynamic from data).
    assert isinstance(f["window"], str) and len(f["window"]) > 0


# --- Pick conviction ----------------------------------------------------------


def test_pick_conviction_shape() -> None:
    pc = _load("pick_conviction.json")
    assert {"series", "latest", "conviction", "methodology"} <= set(pc)
    assert pc["conviction"] in {"high", "low"}
    if pc["series"]:
        for pt in pc["series"]:
            assert {"date", "std", "decile_spread"} <= set(pt)


# --- Enriched picks (name + sector + prob_up) --------------------------------


def test_picks_enriched_schema() -> None:
    """Each pick must carry the enriched display fields + calibrated prob_up."""
    picks = _load("picks.json")
    assert isinstance(picks, list) and len(picks) >= 10
    for p in picks:
        assert {"rank", "ticker", "region", "name", "sector", "score", "prob_up"} <= set(p)
        assert p["region"] in {"us", "cn"}
        assert 0.0 <= p["prob_up"] <= 1.0, f"prob_up out of [0,1]: {p['prob_up']}"
        assert isinstance(p["name"], str)
        assert isinstance(p["sector"], str)


def test_picks_cover_both_regions() -> None:
    """Per-region selection must surface BOTH US and CN (regression for the
    earlier bug where global-latest silently dropped the lagging region)."""
    picks = _load("picks.json")
    regions = {p["region"] for p in picks}
    assert regions == {"us", "cn"}, f"picks must cover both regions, got {regions}"


def test_shorts_enriched_schema() -> None:
    shorts = _load("shorts.json")
    assert isinstance(shorts, list) and len(shorts) >= 3
    for s in shorts:
        assert {"rank", "ticker", "region", "name", "sector", "score", "prob_up"} <= set(s)
        assert 0.0 <= s["prob_up"] <= 1.0


def test_picks_meta_calibration_disclosed() -> None:
    """picks_meta.json must disclose method + walk_forward + per-region meta +
    a disclaimer string that references the null verdict (anti-overclaiming)."""
    meta = _load("picks_meta.json")
    assert meta["method"] in {"platt", "isotonic"}
    assert meta["walk_forward"] is False
    assert isinstance(meta["regions"], dict) and len(meta["regions"]) >= 1
    for region, payload in meta["regions"].items():
        m = payload["meta"]
        assert m["region"] == region
        assert m["n_pairs"] >= 30
        assert 0.0 <= m["base_rate"] <= 1.0
        assert 0.0 <= m["prob_min"] <= m["prob_max"] <= 1.0
    assert isinstance(meta["disclaimer"], str) and len(meta["disclaimer"]) > 50
    assert "NULL" in meta["disclaimer"] or "null" in meta["disclaimer"].lower()


# --- Sector breakdown --------------------------------------------------------


def test_sector_breakdown_shape() -> None:
    sb = _load("sector_breakdown.json")
    assert sb["status"] in {"ok", "awaiting_fetch"}
    if sb["status"] != "ok":
        return
    assert isinstance(sb["top_favored"], list)
    assert isinstance(sb["all_sectors"], list)
    assert sb["n_sectors"] == len(sb["all_sectors"])
    for row in sb["all_sectors"]:
        assert {"sector", "n_stocks", "mean_score", "mean_prob_up"} <= set(row)
        assert row["n_stocks"] >= 3  # min group size enforced by export
        assert 0.0 <= row["mean_prob_up"] <= 1.0


def test_sector_breakdown_methodology_discloses_classification() -> None:
    """The methodology must disclose how sectors are classified (US SIC vs
    A-share board tiers), honestly distinguishing industry from tier."""
    sb = _load("sector_breakdown.json")
    if sb["status"] != "ok":
        return
    assert "board" in sb["methodology"].lower() or "SIC" in sb["methodology"]


# --- Picks backtest (track record: prediction vs reality) --------------------


def test_picks_backtest_shape() -> None:
    """Track record must have months + summary with hit_rate + excess."""
    bt = _load("picks_backtest.json")
    assert {"months", "summary", "methodology"} <= set(bt)
    s = bt["summary"]
    assert s["n_picks"] >= 20
    assert 0.0 <= s["hit_rate"] <= 1.0
    assert isinstance(s["avg_excess"], (int, float))
    for m in bt["months"]:
        expected = {"month", "region", "picks", "top_mean_return", "base_mean_return", "excess"}
        assert expected <= set(m)
        assert m["region"] in {"us", "cn"}
        for p in m["picks"]:
            assert {"ticker", "name", "score", "realized_return", "hit"} <= set(p)
            assert isinstance(p["hit"], bool)


def test_picks_backtest_methodology_mentions_null() -> None:
    """The track record methodology must honestly disclose the null verdict."""
    bt = _load("picks_backtest.json")
    assert "NULL" in bt["methodology"] or "null" in bt["methodology"].lower()


# --- Market context (Trump Era overview) -------------------------------------


def test_market_context_shape() -> None:
    """market_context.json must have VIX + market series + events from 2016."""
    mc = _load("market_context.json")
    assert {"vix_series", "market_series", "events", "methodology"} <= set(mc)
    assert mc["vix_series"][0]["month"] <= "2016-02"
    assert len(mc["vix_series"]) >= 100  # ~10 years monthly
    assert len(mc["market_series"]) >= 100
    # Market index starts at ~100 (2016 rebase).
    first_idx = mc["market_series"][0]["index"]
    assert 90 <= first_idx <= 105, f"first index should be ~100, got {first_idx}"
    # Events are curated + have required fields.
    assert len(mc["events"]) >= 5
    for e in mc["events"]:
        assert {"date", "label", "type", "region"} <= set(e)
        assert e["type"] in {
            "political", "trade", "crisis", "monetary", "inauguration", "fed_pressure",
        }


# --- Model-health / drift monitor (leakage-safe, display-only) ---------------


def test_model_health_shape() -> None:
    """model_health.json: per-region PSI drift + rolling IC, leakage-safe display."""
    mh = _load("model_health.json")
    assert mh["status"] in {"ok", "awaiting_fetch"}
    assert "methodology" in mh
    if mh["status"] != "ok":
        return
    assert "regions" in mh and isinstance(mh["regions"], dict)
    for region, m in mh["regions"].items():
        assert m["region"] == region
        assert m["regime"] in {"stable", "moderate", "significant"}
        assert isinstance(m["psi"], (int, float)) and m["psi"] >= 0
        # Realized-pair counts must be positive integers.
        assert isinstance(m["n_history"], int) and m["n_history"] > 0
        assert isinstance(m["n_recent"], int) and m["n_recent"] > 0
        # IC is bounded in [-1, 1]; base rates in [0, 1].
        assert -1.0 <= m["ic_full"] <= 1.0 and -1.0 <= m["ic_recent"] <= 1.0
        assert 0.0 <= m["base_rate_full"] <= 1.0 and 0.0 <= m["base_rate_recent"] <= 1.0
    # Honest-disclosure: methodology must say it is NOT a retrain trigger.
    assert "retrain" in mh["methodology"].lower() or "not a research" in mh["methodology"].lower()


# --- Seven-theme signal overview (display-only) ------------------------------


def test_themes_shape() -> None:
    """themes.json: per-theme status + signals, honest about non-live themes."""
    th = _load("themes.json")
    assert th["status"] in {"ok", "awaiting_fetch"}
    assert "methodology" in th
    if th["status"] != "ok":
        return
    themes = th["themes"]
    assert isinstance(themes, list) and len(themes) == 7
    keys = {t["key"] for t in themes}
    assert keys == {
        "price", "macro", "fundamentals", "news_sentiment",
        "risk", "net_cost", "market_structure",
    }
    for t in themes:
        assert t["status"] in {"live", "partial", "forward_only", "needs_work"}
        # Live/partial themes must carry real signal values; the honest-empty
        # themes (forward_only/needs_work) must have NO signals (no mock data).
        signals = t.get("signals", [])
        if t["status"] in {"live", "partial"}:
            assert len(signals) >= 1
            for s in signals:
                assert {"name", "value"} <= set(s)
        else:
            assert signals == []
    # Methodology must disclose it is not the frozen Track-B research verdict.
    low = th["methodology"].lower()
    assert "not" in low and ("research" in low or "track-b" in low)


# --- TACO pressure index ------------------------------------------------------


def test_taco_vix_monthly_from_2016() -> None:
    """TACO VIX series is monthly mean from 2016 (full Trump-era stress arc),
    not just recent daily obs — consistent with the market_context baseline."""
    taco = _load("taco.json")
    assert {"vix_series", "events", "methodology"} <= set(taco)
    vs = taco["vix_series"]
    assert len(vs) >= 100, "VIX should span ~10 years monthly"
    for pt in vs:
        assert {"month", "vix"} <= set(pt)
        assert len(pt["month"]) == 7  # YYYY-MM
    assert vs[0]["month"] <= "2016-02"
    # 2025 TACO events partition cleanly into escalations + climbdowns.
    assert taco["escalations_count"] + taco["climbdowns_count"] == len(taco["events"])


# --- Smart money (13D) --------------------------------------------------------


def test_smart_money_yearly_when_present() -> None:
    """Smart-money yearly filing-volume breakdown (mirrors form4 yearly)."""
    sm = _load("smart_money.json")
    assert {"recent_filings", "total_filings", "methodology"} <= set(sm)
    if "yearly" not in sm:
        return  # stale JSON before re-export
    yearly = sm["yearly"]
    assert isinstance(yearly, list)
    if yearly:
        years = [y["year"] for y in yearly]
        assert years == sorted(years), "yearly years must be ascending"
        for y in yearly:
            assert {"year", "filings"} <= set(y)
            assert isinstance(y["filings"], int) and y["filings"] >= 0


# --- Headline provenance + audit-integrity (frozen-config birth certificate) --


def test_metrics_latest_month_is_clean_iso_date() -> None:
    """The hero payload's latest_month must be a clean YYYY-MM-DD string.

    Regression: export_picks once returned ``str(...date)`` where ``.date`` is a
    bound method on Timestamp, producing the Python repr
    ``<bound method Timestamp.date of Timestamp(...)`` into the hero payload.
    """
    m = _load("metrics.json")
    lm = m.get("latest_month", "")
    assert isinstance(lm, str), "latest_month must be a string"
    assert "bound method" not in lm, f"latest_month leaked a Python repr: {lm!r}"
    assert "<" not in lm and ">" not in lm, f"latest_month contains angle brackets: {lm!r}"
    # Must parse as an ISO date (YYYY-MM-DD).
    parts = lm.split("-")
    assert len(parts) == 3 and all(p.isdigit() for p in parts), f"not ISO YYYY-MM-DD: {lm!r}"


def test_metrics_carries_ledger_lineage() -> None:
    """The hero payload must trace to its ledger row (single source of truth).

    Regression: export_metrics hardcoded the IC/p/CI literals with NO ledger_row
    or config_sig, so the two most prominent surfaces (VerdictAnchor +
    ResearchGlance) read an un-traced float. Now the fields are emitted so every
    surface can link the number to its frozen config, and they must agree with
    headline_provenance.json (same climax row).
    """
    m = _load("metrics.json")
    hp = _load("headline_provenance.json")
    assert "ledger_row" in m, "metrics.json missing ledger_row (lineage regression)"
    assert "config_sig_short" in m, "metrics.json missing config_sig_short"
    assert m["ledger_row"] == hp["ledger_row"], (
        "metrics + provenance disagree on climax row (single-source-of-truth break)"
    )
    assert m["config_sig_short"] == hp["config_sig_short"], (
        "metrics + provenance disagree on config sig"
    )


def test_ledger_audit_climax_row_carries_verdict_and_metric() -> None:
    """The confirmatory climax row must carry its real metric + verdict.

    Regression: export_ledger_audit only handled a flat combined_ic scalar, but
    the climax row stores IC as a nested combined_ic.mean dict, so its metric
    rendered empty and the headline claim was mute in its own audit timeline.
    """
    audit = _load("ledger_audit.json")
    entries = audit.get("entries", [])
    confirmatory = [e for e in entries if e.get("event") == "confirmatory:first"]
    assert confirmatory, "ledger audit has no confirmatory:first row"
    climax = confirmatory[-1]
    assert climax.get("metric"), "climax row metric is empty (nested-dict extraction regression)"
    assert climax.get("verdict"), "climax row verdict is empty"
    assert climax.get("h6") is True, "climax row must assert H6 determinism"
    assert "combined_IC=" in climax["metric"], f"unexpected metric format: {climax['metric']}"


def test_headline_provenance_freeze_before_result() -> None:
    """The headline claim's birth certificate must prove freeze-before-result.

    The hero number (combined rank-IC) is tied to its ledger row and to the
    config_committed row sharing its sha256 that was written BEFORE the result.
    This is the anti-leakage contract surfaced at the point of the claim.
    """
    p = _load("headline_provenance.json")
    assert p["status"] == "ok", "headline provenance should be resolved"
    h = p["headline"]
    assert h["combined_ic"] is not None and isinstance(h["combined_ic"], float)
    assert h["h6_deterministic"] is True
    assert h["jt_look1"] == "NOT_EQUIVALENT"
    freeze = p["freeze"]
    assert freeze is not None, "freeze row must be present"
    # Same sha256 prefix shared by freeze + result = the same frozen config.
    assert p["config_sig_short"] == freeze["config_sig_short"], (
        "freeze and result config sigs must match (same frozen config)"
    )
    # Freeze row precedes result row in the ledger.
    assert freeze["ledger_row"] < p["ledger_row"], (
        "freeze row must precede result row (config_committed BEFORE result)"
    )
    # The contract flag is the terminal-facing summary of the above checks.
    assert p["contract"]["freeze_before_result"] is True


def test_ledger_append_only_not_mutated_by_export() -> None:
    """The ledger file must be unchanged by the READ-ONLY audit exports.

    These exports project runs/ledger.jsonl into browser JSON; they must never
    rewrite the append-only audit log. Guard the file's committed state.
    """
    import hashlib

    ledger = Path("runs/ledger.jsonl")
    if not ledger.exists():
        return  # fresh CI checkout may lack the gitignored ledger
    digest = hashlib.sha256(ledger.read_bytes()).hexdigest()
    # Snapshot the known-good committed digest. If the ledger legitimately grows
    # (a new research row is appended) this will fail — that is correct: a human
    # must re-pin it after verifying the new row is append-only.
    assert digest == "44157b5b0d47b4838bec53d3b1509ff2ed29a808683072a79b44693a636f70ee", (
        f"ledger sha256 changed to {digest}; re-verify append-only then re-pin"
    )
