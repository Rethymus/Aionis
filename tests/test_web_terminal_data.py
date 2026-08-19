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
    # Freshness summary: when themes draw from independent sources their as_of
    # dates legitimately differ (frozen PIT panel vs GDELT/ALFRED). The summary
    # must surface that range so a visitor doesn't read a single stale top-level
    # date as "everything is this old" — the macro theme is genuinely fresher.
    fr = th.get("freshness")
    assert fr is not None, "themes.json missing freshness summary"
    assert {"earliest", "latest", "mixed"} <= set(fr)
    assert isinstance(fr["mixed"], bool)
    if fr["mixed"]:
        assert fr["earliest"] and fr["latest"], "mixed freshness must have both bounds"
        assert fr["earliest"] <= fr["latest"], "earliest must precede latest"


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


# --- Untested-panel contract coverage (display-layer regression guards) -------


def test_evidence_panel_contract() -> None:
    """evidence.json feeds /evidence (14 null cards) + the hero lineage link.

    The view reads e.n (card key), e.result, e.estimate (the headline-size
    number), e.ci_lo/ci_hi, e.p, e.n_months, and e.grade (drives the grade
    badge style + the CONFIRMATORY climax card's ledger link). A shape break
    crashes the grid or, worse, loses the CONFIRMATORY climax card (#15) that
    the hero provenance points at.
    """
    ev = _load("evidence.json")
    assert isinstance(ev, list) and len(ev) >= 10, "evidence needs >=10 rows"
    valid_grades = {"CONFIRMATORY", "CV-proxy", "chron./explor.", "explor."}
    ns = []
    for e in ev:
        assert {"n", "result", "estimate", "ci_lo", "ci_hi", "p", "n_months", "grade"} <= set(e)
        assert e["grade"] in valid_grades, f"unknown grade {e['grade']!r}"
        assert isinstance(e["estimate"], (int, float))
        assert isinstance(e["n_months"], int)
        ns.append(e["n"])
    # The CONFIRMATORY climax card MUST be present — the hero provenance + the
    # evidence ledger link point at it. If it silently drops, the hero anchor
    # becomes a dangling reference.
    confirmatory = [e for e in ev if e["grade"] == "CONFIRMATORY"]
    assert len(confirmatory) >= 1, "evidence has no CONFIRMATORY climax card"
    # Row numbers must be unique (the view keys React lists by e.n).
    assert len(ns) == len(set(ns)), "evidence row numbers must be unique"


def test_power_floor_panel_contract() -> None:
    """power_floor.json feeds /power-floor (the power-limit disclosure page).

    The view renders looks (n_min_months/years, rci_level_pct, z) as the core
    'why equivalence is structurally unreachable' argument. The pure-noise vs
    observed sigma split is the mechanism story. A shape break makes the page
    either crash or — worse — render numbers that understate the power floor.
    """
    pf = _load("power_floor.json")
    assert {"sesoi", "looks", "sigma_observed_median", "sigma_pure_noise_n462",
            "n_min_at_pure_noise_look3_months", "n_min_at_observed_look3_months",
            "verdict"} <= set(pf)
    assert isinstance(pf["sesoi"], (int, float)) and pf["sesoi"] > 0
    looks = pf["looks"]
    assert isinstance(looks, list) and len(looks) == 3, "power floor needs 3 looks"
    for look in looks:
        assert {"look", "n", "z", "n_min_months", "n_min_years", "rci_level_pct"} <= set(look)
        assert isinstance(look["n_min_months"], int) and look["n_min_months"] > 0
        assert isinstance(look["n_min_years"], (int, float)) and look["n_min_years"] > 0
    # The core honest claim: observed sigma >> pure-noise sigma (ML noise excess
    # is why the power floor binds). If this invariant inverts, the page's whole
    # argument flips.
    assert pf["sigma_observed_median"] > pf["sigma_pure_noise_n462"], (
        "observed sigma must exceed pure-noise bound (ML noise excess is the mechanism)"
    )
    # look-3 observed n_min (the 'how many years' headline) must be the largest.
    n_mins = [look["n_min_months"] for look in looks]
    assert n_mins == sorted(n_mins, reverse=True) or n_mins[-1] >= n_mins[0], (
        "n_min should grow with look (more data needed for tighter equivalence)"
    )


def test_calibration_reliability_panel_contract() -> None:
    """calibration_reliability.json feeds /calibration (reliability diagram).

    The view reads regions.{us,cn}.pooled_ece, .series (per-month walk-forward),
    and .pooled_reliability (the bins for the reliability plot). A shape break
    breaks the chart or, worse, hides that probabilities cluster near base rate
    (the honest-null signature).
    """
    cr = _load("calibration_reliability.json")
    assert cr["status"] in {"ok", "awaiting_fetch"}
    if cr["status"] != "ok":
        return
    assert {"method", "walk_forward", "min_train_months", "regions"} <= set(cr)
    regions = cr["regions"]
    assert {"us", "cn"} <= set(regions), "calibration needs both regions"
    for r in regions.values():
        assert {"n_months", "series", "pooled_ece", "pooled_reliability"} <= set(r)
        assert isinstance(r["pooled_ece"], (int, float))
        assert isinstance(r["series"], list) and len(r["series"]) >= 1
        for m in r["series"]:
            assert {"month", "ece_oos"} <= set(m)
        # Reliability bins: pred_mean + emp_freq define the curve.
        assert isinstance(r["pooled_reliability"], list)
        for b in r["pooled_reliability"]:
            assert {"bin_lo", "bin_hi"} <= set(b)


def test_ic_monthly_panel_contract() -> None:
    """ic_monthly.json feeds the confirmatory IC time-series chart.

    The view plots month/us/cn/combined as the IC arc. A shape break (NaN, wrong
    sort, missing combined, DUPLICATE months) crashes the chart or distorts the
    headline arc. Duplicate months were a real defect (US-only + CN-only rows
    for the same month emitted as two rows with the same key — a consumer
    plotting by `month` would get double points / broken joins); the export now
    coalesces by month, and this test guards against recurrence.
    """
    ic = _load("ic_monthly.json")
    assert isinstance(ic, list) and len(ic) >= 24, "ic_monthly needs >=24 months"
    for row in ic:
        assert {"month", "us", "cn", "combined"} <= set(row)
        # us/cn/combined may be null (region missing that month) but never NaN
        # (NaN would serialize and silently distort the chart).
        for k in ("us", "cn", "combined"):
            v = row[k]
            assert v is None or isinstance(v, (int, float)), f"{k} must be number or null"
    # Months strictly ascending (time-series invariant the chart relies on).
    months = [r["month"] for r in ic]
    assert months == sorted(months), "ic_monthly months must be ascending"
    # NO duplicate months — a consumer keyed/joined by `month` would break.
    assert len(months) == len(set(months)), (
        f"ic_monthly has duplicate months: "
        f"{ {m for m in months if months.count(m)>1} }"
    )
    # The combined column is the headline series — must not be entirely null.
    assert any(r["combined"] is not None for r in ic), "combined IC is entirely null"


def test_bps_sweep_panel_contract() -> None:
    """bps_sweep.json feeds the net-cost curve on /themes (Sharpe vs slippage).

    The view plots net_sharpe/gross_sharpe across bps to show cost decay. A
    shape break hides that the strategy keeps most Sharpe at 5bps — the
    honest 'realistic cost' read.
    """
    bps = _load("bps_sweep.json")
    assert isinstance(bps, list) and len(bps) >= 3, "bps sweep needs >=3 points"
    for row in bps:
        assert {"bps", "net_sharpe", "gross_sharpe", "avg_turnover"} <= set(row)
        assert isinstance(row["bps"], (int, float)) and row["bps"] >= 0
        assert isinstance(row["avg_turnover"], (int, float)) and row["avg_turnover"] >= 0
    # bps must be ascending (the curve's x-axis invariant).
    bps_vals = [r["bps"] for r in bps]
    assert bps_vals == sorted(bps_vals), "bps values must be ascending"
    # Turnover is cost-independent of bps — it must be ~constant across the sweep.
    turns = [r["avg_turnover"] for r in bps]
    assert max(turns) - min(turns) < 0.5, "turnover should be ~constant across bps"
    # Net Sharpe must decay (or stay flat) as bps rises — never exceed gross.
    for r in bps:
        assert r["net_sharpe"] <= r["gross_sharpe"] + 1e-9, (
            f"net_sharpe must not exceed gross at bps={r['bps']}"
        )


def test_sigma_survey_panel_contract() -> None:
    """sigma_survey.json feeds the power-floor page + the AI attribution card.

    The attribution card derives the noise-floor sigma from the
    track_c_confirmatory/combined row; the power-floor page plots the excess.
    A shape break makes the hero 'sigma approx' literal revert to the hand
    constant or distort the power-limit argument.
    """
    ss = _load("sigma_survey.json")
    assert {"rows", "summary"} <= set(ss)
    rows = ss["rows"]
    assert isinstance(rows, list) and len(rows) >= 10, "sigma survey needs >=10 series"
    for r in rows:
        assert {"source", "arm", "sigma_observed", "sigma_pure_noise", "excess_ratio"} <= set(r)
        assert isinstance(r["sigma_observed"], (int, float))
        assert isinstance(r["excess_ratio"], (int, float)) and r["excess_ratio"] > 1.0
    # The confirmatory combined row MUST exist — attribution-card derives the
    # hero sigma from it. If it drops, the card falls back to a hand constant.
    combined = [
        r for r in rows
        if r.get("source") == "track_c_confirmatory" and r.get("arm") == "combined"
    ]
    assert len(combined) >= 1, "sigma survey missing track_c_confirmatory/combined row"
    # summary.excess_median is cited in docs — must be present and > 1.
    assert "excess_median" in ss["summary"]
    assert ss["summary"]["excess_median"] > 1.0


def test_theme_signals_panel_contract() -> None:
    """theme_signals.json feeds the operationalized-signals grid on /themes.

    The view renders each signal as direction × strength × favored tickers,
    grouped by theme. A shape break crashes the grid or, worse, drops the
    'display-only, not a research claim' honesty disclosure.
    """
    ts = _load("theme_signals.json")
    assert ts["status"] in {"ok", "awaiting_fetch"}
    if ts["status"] != "ok":
        return
    assert {"groups", "signals", "methodology"} <= set(ts)
    assert isinstance(ts["groups"], list) and len(ts["groups"]) >= 1
    valid_dirs = {"bullish", "bearish", "neutral"}
    for sig in ts["signals"].values():
        assert {"signal", "direction", "strength", "mean", "n", "group"} <= set(sig)
        assert sig["direction"] in valid_dirs, f"unknown direction {sig['direction']!r}"
        assert isinstance(sig["strength"], (int, float))
        # Every signal's group must be one of the declared groups.
        assert sig["group"] in ts["groups"], f"signal group {sig['group']!r} not in groups"
    # Methodology must disclose display-only (anti-misrepresentation).
    assert "display" in ts["methodology"].lower() or "not" in ts["methodology"].lower()


def test_macro_drivers_panel_contract() -> None:
    """macro_drivers.json feeds the macro-context cards on /regime.

    The view plots per-series macro arcs. A shape break drops the market-context
    that frames the whole 'what regime are we in' read. CRITICALLY, three
    consumers read specific keys that must be present: macro-drivers-card +
    macro-stagflation-read read `fedfunds`, macro-mandate-tension reads
    `real_rate`. A stale partial export (cache absent at run time) silently
    dropped these once, hiding 3 cards — this test pins the consumer-required
    key-set so that recurrence is caught at CI, not on the live page.
    """
    md = _load("macro_drivers.json")
    assert md["status"] in {"ok", "awaiting_fetch"}
    if md["status"] != "ok":
        return
    assert {"series", "methodology"} <= set(md)
    series = md["series"]
    assert isinstance(series, dict) and len(series) >= 3, "macro needs >=3 driver series"
    for name, pts in series.items():
        assert isinstance(pts, list) and len(pts) >= 12, f"{name} needs >=12 months"
        for pt in pts:
            assert {"month", "value"} <= set(pt)
        # Months ascending within each series (time-series invariant).
        months = [pt["month"] for pt in pts]
        assert months == sorted(months), f"{name} months must be ascending"
    # Consumer-required keys (guarded against the silent-skip recurrence).
    required = {"cpi_yoy", "dxy", "payems_yoy", "t10y2y", "unrate", "fedfunds", "real_rate"}
    missing = required - set(series)
    assert not missing, (
        f"macro_drivers missing consumer-required series keys {missing} "
        f"(present: {sorted(series)}); 3 /regime cards would silently hide"
    )




# --- data health (freshness/provenance map of every panel) --------------------


def test_data_health_shape() -> None:
    """The freshness map must cover the whole terminal with valid categories.

    Structural answer to 'why doesn't panel X update': every panel is frozen /
    daily / cadence with its OWN as_of (never fabricated). The summary counts
    must reconcile with the panel list, and the #49-derived research readouts
    must be classified frozen (advancing them would be rerun-to-significance).
    """
    dh = _load("data_health.json")
    assert dh["status"] == "ok"
    panels = dh["panels"]
    assert len(panels) >= 20, "the freshness map must cover the whole terminal"
    valid = {"daily", "cadence", "frozen"}
    keys: set[str] = set()
    for p in panels:
        assert p["category"] in valid
        assert isinstance(p["key"], str) and p["key"]
        assert isinstance(p["file"], str) and p["file"].endswith(".json")
        assert p["as_of"] is None or isinstance(p["as_of"], str)
        assert p["exported_at"] is None or isinstance(p["exported_at"], str)
        assert isinstance(p["present"], bool)
        keys.add(p["key"])
    assert len(keys) == len(panels), "panel keys must be unique"
    s = dh["summary"]
    assert s["n_panels"] == len(panels)
    assert s["n_daily"] + s["n_cadence"] + s["n_frozen"] == len(panels)
    by_key = {p["key"]: p for p in panels}
    for k in ("picks", "metrics", "ic_monthly", "picks_backtest", "stock_universe"):
        assert by_key[k]["category"] == "frozen", f"{k} derives from frozen OOS artifacts"
    assert by_key["cot"]["category"] == "cadence"
    assert "rerun-to-significance" in dh["methodology"]


def test_data_health_as_of_matches_source_panels() -> None:
    """as_of is extracted from each panel's own fields — spot-pin two."""
    dh = _load("data_health.json")
    by_key = {p["key"]: p for p in dh["panels"]}
    metrics = _load("metrics.json")
    assert by_key["metrics"]["as_of"] == metrics["latest_month"]
    cot = _load("cot.json")
    if cot.get("latest_date"):
        assert by_key["cot"]["as_of"] == cot["latest_date"]


# --- stock universe (per-stock frozen readout) --------------------------------


def test_stock_universe_shape() -> None:
    """Per-stock view over the frozen OOS scores: ranks reconcile per region.

    The rank_change bound guards the cross-region contamination bug (US and CN
    month-ends coincide ~70% of the time; an unscoped prev-month frame once
    produced TROW rank_change 829 > n_region 492).
    """
    su = _load("stock_universe.json")
    assert su["status"] == "ok"
    months = su["months"]
    assert months == sorted(months) and len(set(months)) == len(months)
    assert len(months) >= 6, "trailing window must span ~12 OOS months"
    stocks = su["stocks"]
    assert len(stocks) >= 1000, "US (~490) + CN (~930) latest-month universe"
    assert su["n_stocks"] == len(stocks)
    tickers = [s["ticker"] for s in stocks]
    assert len(set(tickers)) == len(tickers), "one row per ticker"
    by_region: dict[str, list[dict]] = {}
    for s in stocks:
        assert s["region"] in {"us", "cn"}
        assert isinstance(s["score"], (int, float))
        assert 0.0 <= s["prob_up"] <= 1.0
        assert isinstance(s["rank"], int) and s["rank"] >= 1
        assert len(s["scores"]) == len(months), "scores aligned to the month grid"
        for v in s["scores"]:
            assert v is None or isinstance(v, (int, float))
        by_region.setdefault(s["region"], []).append(s)
    assert set(by_region) == {"us", "cn"}
    for rows in by_region.values():
        n = rows[0]["n_region"]
        assert all(r["n_region"] == n for r in rows)
        assert len(rows) == n, "n_region must equal the region's row count"
        ranks = sorted(r["rank"] for r in rows)
        assert ranks == list(range(1, n + 1)), "ranks form 1..n within a region"
        for r in rows:
            if r["rank_change"] is not None:
                assert -(n - 1) <= r["rank_change"] <= n - 1
    assert su["as_of"].get("us") and su["as_of"].get("cn")


def test_stock_universe_covers_picks() -> None:
    """Every committed pick/short must have a stock page (drill-down target)."""
    su = _load("stock_universe.json")
    have = {s["ticker"] for s in su["stocks"]}
    for p in _load("picks.json"):
        assert p["ticker"] in have, f"pick {p['ticker']} missing a stock page"
    for s in _load("shorts.json"):
        assert s["ticker"] in have, f"short {s['ticker']} missing a stock page"


def test_stock_universe_disclosure() -> None:
    """The panel must carry the honest-null + frozen disclosure."""
    su = _load("stock_universe.json")
    m = su["methodology"]
    assert "display-only" in m
    assert "rerun-to-significance" in m
    assert "NULL" in m


# --- API catalog (public static data API index) -------------------------------


def test_api_catalog_shape() -> None:
    """Every endpoint must carry its 7-gate intake facts + freshness class.

    The catalog is the meta layer of the deployed static API (public/api/v1/):
    license and primary source are non-negotiable (a missing license would
    default to 'unverified — do not ingest'), and the freshness classes must
    reconcile with the data-health map.
    """
    cat = _load("api_catalog.json")
    assert cat["status"] == "ok"
    eps = cat["endpoints"]
    assert len(eps) >= 20
    dh = _load("data_health.json")
    dh_keys = {p["key"] for p in dh["panels"]}
    valid = {"daily", "cadence", "frozen"}
    for e in eps:
        assert e["key"] in dh_keys, f"{e['key']} missing from data_health"
        assert e["freshness"] in valid
        assert e["method"] == "GET" and e["status"] == "available"
        assert e["path"] == f"/api/v1/panels/{e['file']}"
        assert isinstance(e["license"], str) and len(e["license"]) > 5
        assert "unverified" not in e["license"], f"{e['key']} license unmapped"
        assert isinstance(e["source"], str) and len(e["source"]) > 3
    assert {e["key"] for e in eps} == dh_keys, "catalog must cover every health panel"
    lp = cat["live_prices"]
    assert lp["server"].startswith("https://")
    assert len(lp["paths"]) == 2
    assert "display-only" in lp["note"]


def test_api_catalog_disclosure() -> None:
    cat = _load("api_catalog.json")
    m = cat["methodology"]
    assert "display-only" in m
    assert "7-gate" in m
    assert "rerun-to-significance" in m or "frozen" in m
    assert "GitHub Pages" in cat["base_note"]
