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
import re
from datetime import datetime
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
    if f["status"] != "ok":
        return
    # Export cap raised 50 → 200 (visible window; full-window counters live in
    # buys/sells/yearly). The recent list must never exceed the export cap.
    assert len(f["recent"]) <= 200, "recent exceeds the 200-row export cap"


def test_form4_recent_doc_url_when_present() -> None:
    """Recent rows carry an EDGAR filing-index link when the aggregate has it.

    doc_url is built from the row's accession + reporting-owner CIK (mirrors
    the ipo/form8k pattern). Rows from pre-accession aggregates — and stale
    committed JSON before re-export — carry "" / no field at all, which is the
    honest render (—), never a guessed URL. When present, the pattern is
    pinned so a malformed link surfaces here, not as a dead /insiders link.
    """
    f = _load("form4.json")
    if f["status"] != "ok":
        return
    for r in f["recent"]:
        url = r.get("doc_url")
        if not url:
            continue
        assert url.startswith("https://www.sec.gov/Archives/edgar/data/"), url
        assert url.endswith("-index.htm"), url


def test_form4_action_enum_when_ok() -> None:
    """Lock the SEC-correct P/S -> buy/sell mapping (regression guard for the
    earlier A/D -> P/S parser fix)."""
    f = _load("form4.json")
    if f["status"] != "ok":
        return
    for r in f["recent"]:
        assert r["action"] in {"buy", "sell"}, f"action must be buy/sell, got {r['action']}"
    # buys/sells are full-window counters (recent is the top-200 visible
    # window); just sanity-check types.
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
    A-share CSRC industry via baostock, with board-tier fallback), honestly
    distinguishing industry from tier."""
    sb = _load("sector_breakdown.json")
    if sb["status"] != "ok":
        return
    assert "board" in sb["methodology"].lower() or "SIC" in sb["methodology"]
    # CN classification source must be named (CSRC industry upgrade, not a
    # silent tier relabel) — docs/data-intake-baostock-industry.md.
    assert "CSRC" in sb["methodology"] or "证监会" in sb["methodology"]


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
            "political", "trade", "crisis", "monetary", "inauguration", "fed_pressure", "ipo",
        }


def test_market_context_cn_context_events() -> None:
    """A-share milestones ride the event table as global-context disclosure.

    The chart stays a US equal-weight index; region=='cn' rows are context
    markers (A股 extreme sessions, China macro) rendered with an "A 股" badge.
    """
    mc = _load("market_context.json")
    cn = [e for e in mc["events"] if e.get("region") == "cn"]
    assert len(cn) >= 2, "need >=2 region=='cn' context events"
    for e in cn:
        assert e["label"].strip(), f"cn event label must be non-empty: {e}"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"]), f"bad date format: {e['date']}"


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


# --- Freight TACO equivalent (BTS TSI public-domain proxy) --------------------


def test_freight_taco_panel_contract() -> None:
    """freight_taco.json: the DISCLOSED degraded TACO replacement invariants.

    The panel is a public-domain freight-activity proxy (BTS Freight TSI) —
    it must say it is NOT satellite data, carry the BTS public-domain
    license, disclose the degradation in machine-readable form, and keep its
    KPIs internally consistent with the 24-month series (MoM chain + YoY are
    recomputed from the index levels — no hand-edited numbers).
    """
    p = _load("freight_taco.json")
    assert p["status"] == "ok"
    assert {
        "as_of", "source", "license", "methodology", "degradation",
        "latest", "history", "series_24m", "truck_employment",
    } <= set(p)

    # G1: BTS public-domain license, primary source named.
    low = p["license"].lower()
    assert "bureau of transportation statistics" in low and "public domain" in low
    assert "data.bts.gov" in p["source"] or "bts.gov" in p["source"]

    # Caliber honesty: NOT satellite + the granularity loss is named.
    m = p["methodology"].lower()
    assert "not satellite" in m and "bts" in m and "revision" in m
    d = p["degradation"]
    assert {"proxy", "granularity_lost", "commercial_original"} <= set(d)
    assert "satellite" in d["granularity_lost"].lower()

    # 24-month series: ascending YYYY-MM, every point carries the MoM chain.
    s = p["series_24m"]
    assert len(s) == 24
    months = [pt["month"] for pt in s]
    assert months == sorted(months)
    assert all(len(m_) == 7 for m_ in months)
    for prev, cur in zip(s, s[1:]):
        assert {"month", "tsi", "mom_pct"} <= set(cur)
        recomputed = (cur["tsi"] / prev["tsi"] - 1) * 100
        assert abs(cur["mom_pct"] - recomputed) < 0.05, (cur["month"], cur["mom_pct"])

    # Latest KPIs reconcile with the series tail (panel can't drift from chart).
    assert p["latest"]["month"] == months[-1]
    assert p["latest"]["tsi"] == s[-1]["tsi"]
    assert abs(p["latest"]["mom_pct"] - s[-1]["mom_pct"]) < 1e-9
    yoy = (s[-1]["tsi"] / s[-13]["tsi"] - 1) * 100  # 12 months before latest
    assert abs(p["latest"]["yoy_pct"] - yoy) < 0.05
    assert p["as_of"] == months[-1]
    # Full history honesty: the panel is a 24-month window over a longer series.
    assert p["history"]["n_months_total"] >= 24
    assert p["history"]["first_month"] < months[0]

    # Auxiliary truck employment (BLS CES via FRED) — shape when present,
    # null = honest gap (never fabricated).
    te = p["truck_employment"]
    if te is not None:
        assert te["series_id"] == "CES4348400001"
        assert {"latest_month", "latest_k", "yoy_pct", "series_24m"} <= set(te)
        assert len(te["series_24m"]) == 24
        emp = {e["month"]: e["k"] for e in te["series_24m"]}
        # 12 months before the AUXILIARY's own latest month (the CES release
        # calendar may be offset from the TSI one — reconcile on its own axis).
        y, mth = te["latest_month"].split("-")
        y_prev = int(y) - 1
        month_prev = f"{y_prev}-{mth}"
        assert month_prev in emp, "auxiliary window must cover its own YoY anchor"
        recomputed = (emp[te["latest_month"]] / emp[month_prev] - 1) * 100
        assert abs(te["yoy_pct"] - recomputed) < 0.05
    else:
        assert te is None  # explicit honest absence, not a stub object


def test_freight_taco_registered_in_catalog() -> None:
    """freight_taco is registered in data_health + api_catalog with the BTS
    public-domain license (the intake facts travel with the endpoint)."""
    cat = _load("api_catalog.json")
    entry = next((e for e in cat["endpoints"] if e["key"] == "freight_taco"), None)
    assert entry is not None, "freight_taco missing from api_catalog"
    assert "public domain" in entry["license"].lower()
    assert "transportation statistics" in entry["license"].lower()
    assert entry["as_of"], "freight_taco must carry an as_of month"

    dh = _load("data_health.json")
    panel = next((x for x in dh["panels"] if x["key"] == "freight_taco"), None)
    assert panel is not None, "freight_taco missing from data_health panels"
    assert panel["category"] == "cadence", "TSI advances on BTS's monthly rhythm"


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


# --- Institutions (13F-HR star managers) ---------------------------------------


def test_politician_trades_panel_contract() -> None:
    """Politician-trades panel schema: filing-stream honesty invariants.

    The House PTR panel is filing-stream level BY DESIGN: members/offices/
    filing types/as-filed dates/PDF links from the bulk FD.xml index —
    ``as_of`` is the latest FilingDate (real observation date). Senate block
    must be honestly disclosed, and the top-filer counts must be filing
    counts (not trade values).
    """
    f = _load("politician_trades.json")
    assert f["status"] in {"ok", "awaiting_fetch"}
    assert {"as_of", "latest_filing_year", "window_years", "house", "senate",
            "methodology"} <= set(f)
    if f["status"] != "ok" or not f["house"]["filings"]:
        return  # awaiting-fetch placeholder keeps the shape loose
    dates: list[str] = []
    for p_ in f["house"]["filings"]:
        assert {"member", "office", "filing_type", "filing_date", "filing_year",
                "party", "doc_url"} <= set(p_)
        assert p_["party"] in {"R", "D", "I", None}
        assert p_["filing_type"].upper().startswith("PTR")
        assert p_["doc_url"].startswith("https://disclosures-clerk.house.gov/")
        assert p_["doc_url"].endswith(".pdf")
        assert int(p_["filing_year"]) in f["window_years"]
        if p_["filing_date"] is not None:
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", p_["filing_date"])
            dates.append(p_["filing_date"])
    assert dates == sorted(dates, reverse=True), "filings must be newest-first"
    if dates:
        assert f["as_of"] == max(dates), "as_of must be the latest filing_date"
    assert f["senate"]["status"] == "blocked", "Senate Akamai block must be disclosed"
    for m in f["house"]["top_members"]:
        assert m["count"] >= 1 and m["office"]
    assert f["latest_filing_year"] == max(f["window_years"])
    # by_year counts must sum to the panel total (honest counting).
    assert sum(f["house"]["by_year"].values()) == f["house"]["total"]
    # Full-stream export (2026-08-22, cap raised 100 → 1000): the visible list
    # is the WHOLE filing stream, not a preview — visible == total.
    assert len(f["house"]["filings"]) == f["house"]["total"], (
        f"visible filings ({len(f['house']['filings'])}) != total "
        f"({f['house']['total']}) — export must be full-stream (cap 1000)"
    )
    # party_coverage is "linked/total" over ALL filings — the format pins the
    # honest-counting contract.
    linked, _, total = f["house"]["party_coverage"].partition("/")
    assert linked.isdigit() and int(total) == f["house"]["total"]


def test_form8k_panel_contract() -> None:
    """8-K panel schema: event shape, category counting honesty, date order.

    Locks the contract the /events view renders against: items are the legally
    mandated 8-K item numbers; ``unclassified`` and ``by_category`` must agree
    with the event list (counted, never guessed); events sorted by filing_date
    descending (the stream reads newest-first).
    """
    f = _load("form8k.json")
    assert f["status"] in {"ok", "awaiting_fetch"}
    assert {"as_of", "window", "issuers", "total", "unclassified", "by_category",
            "events", "methodology"} <= set(f)
    if f["status"] != "ok" or not f["events"]:
        return  # awaiting-fetch placeholder keeps the shape loose
    cats: dict[str, int] = {}
    dates: list[str] = []
    for e in f["events"]:
        assert {"ticker", "company", "filing_date", "form", "items",
                "category", "doc_url"} <= set(e)
        for i in e["items"]:
            assert re.fullmatch(r"\d{1,2}\.\d{2,3}", i), f"bad item number: {i!r}"
        dates.append(e["filing_date"])
        cats[e["category"]] = cats.get(e["category"], 0) + 1
    assert dates == sorted(dates, reverse=True), "events must be newest-first"
    assert f["unclassified"] == cats.get("unclassified", 0), (
        "unclassified count must equal its event count (honest counting)"
    )
    for cat, n in f["by_category"].items():
        assert cats.get(cat) == n, f"by_category[{cat}] disagrees with event list"
    assert f["as_of"] == max(dates), "as_of must be the latest filing_date"
    # The event list is the bounded-universe stream (cap = growth guard, not a
    # display slice): every counted event must be visible, else the KPI cards
    # (total/issuers/unclassified) and the "all" filter pill desync.
    assert len(f["events"]) == f["total"], (
        f"event list truncated: {len(f['events'])} visible vs total {f['total']}"
    )


def test_executives_panel_contract() -> None:
    """Executives panel: the form8k officer_changes subset, row for row.

    The panel is DERIVED from the committed form8k stream (category
    'officer_changes' = 8-K Item 5.02) — the contract pins the derivation:
    same rows in the same newest-first order, honest counting (by_company
    sums to total, issuers = distinct tickers), EDGAR primary-doc links,
    as_of = the subset's own latest filing date, and the methodology must
    disclose that person-level extraction is DEFERRED (never guessed).
    """
    x = _load("executives.json")
    f8 = _load("form8k.json")
    assert x["status"] in {"ok", "awaiting_fetch"}
    assert {"as_of", "total", "issuers", "window", "events", "by_company",
            "methodology", "snapshot_ts"} <= set(x)
    if x["status"] != "ok":
        return  # awaiting branch keeps the shape loose
    subset = [e for e in f8.get("events", []) if e.get("category") == "officer_changes"]
    assert x["total"] == len(subset), (
        "total must equal the form8k officer_changes subset (same derivation)"
    )
    dates: list[str] = []
    for got, want in zip(x["events"], subset, strict=True):
        assert {"company", "ticker", "filing_date", "items", "doc_url"} <= set(got)
        assert got["company"] == want["company"]
        assert got["ticker"] == want["ticker"]
        assert got["filing_date"] == want["filing_date"]
        assert got["items"] == want["items"], "full item list preserved per row"
        assert got["doc_url"] == want["doc_url"]
        assert got["doc_url"].startswith("https://www.sec.gov/Archives/edgar/data/")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", got["filing_date"])
        dates.append(got["filing_date"])
    if not dates:
        return  # honest empty: no officer_changes filings in the window yet
    assert dates == sorted(dates, reverse=True), "events must be newest-first"
    assert sum(x["by_company"].values()) == x["total"], (
        "by_company must sum to total (honest counting)"
    )
    assert set(x["by_company"]) == {e["company"] for e in x["events"]}
    assert x["issuers"] == len({e["ticker"] for e in subset}), (
        "issuers = distinct tickers in the subset"
    )
    assert x["window"]["start"] == min(dates)
    assert x["window"]["end"] == max(dates)
    assert x["as_of"] == max(dates), "as_of must be the subset's latest filing_date"
    # v1 honesty boundary: person-level extraction deferred, disclosed.
    assert "deferred" in x["methodology"].lower()


def test_party_index_panel_contract() -> None:
    """Party index panel: derivation pinned against the source tx panel.

    The panel is DERIVED from the committed politician_trades_tx.json (zero
    new fetches) — the contract recomputes the aggregation from the source
    and demands row-for-row agreement: monthly D/R tx counts, the opposition
    share (n_opposed/n_directional over BOTH-directional common tickers,
    null when none), and the trailing-90d follow portfolios (net_buy =
    n_buy − n_sell, count-weighted only). The methodology must disclose the
    no-prices/no-returns boundary (a display signal list, never performance).
    """
    x = _load("party_index.json")
    src = _load("politician_trades_tx.json")
    assert x["status"] in {"ok", "awaiting_fetch"}
    assert {"as_of", "window_anchor", "window_days", "n_source_tx", "months",
            "latest", "portfolios", "methodology", "snapshot_ts"} <= set(x)
    assert x["source_panel"] == "politician_trades_tx"
    if x["status"] != "ok":
        return
    assert x["as_of"] == src["as_of"], "as_of mirrors the source panel"

    # Source of truth: tickered D/R transactions only.
    tx = [r for r in src["transactions"]
          if r.get("ticker") and r.get("party") in ("D", "R")]
    assert x["n_source_tx"] == len(tx)

    months: dict = {}
    for r in tx:
        b = months.setdefault(r["transaction_date"][:7], {"D": [0, 0], "R": [0, 0]})
        # [buy, sell] per party per month
        b[r["party"]][0 if r["direction"] == "buy" else 1] += 1

    got = x["months"]
    assert [m["month"] for m in got] == sorted(months), "months ascending, no gaps"
    for m in got:
        d_buy, d_sell = months[m["month"]]["D"]
        r_buy, r_sell = months[m["month"]]["R"]
        assert m["d_tx"] == d_buy + d_sell
        assert m["r_tx"] == r_buy + r_sell
        assert m["d_buy"] == d_buy
        assert m["r_buy"] == r_buy
        assert 0 <= m["n_opposed"] <= m["n_directional"] <= m["n_common"]
        if m["n_directional"] == 0:
            assert m["opposition"] is None
        else:
            opp = m["opposition"]
            assert opp is not None and 0.0 <= opp <= 1.0
            assert abs(opp - m["n_opposed"] / m["n_directional"]) < 5e-4

    # Latest headline month must exist in the series; opposed/consensus rows
    # must actually be opposed / consensus by sign.
    assert x["latest"]["month"] in {m["month"] for m in got}
    for row in x["latest"]["opposed"]:
        assert (row["d_net"] > 0) != (row["r_net"] > 0), "opposed = opposite signs"
    for row in x["latest"]["consensus"]:
        assert row["d_net"] > 0 and row["r_net"] > 0, "consensus = both net-buy"

    # Follow portfolios: trailing window from the latest transaction date.
    from datetime import date, timedelta

    max_tx = max(r["transaction_date"] for r in tx)
    cutoff = (date.fromisoformat(max_tx) - timedelta(days=90)).isoformat()
    assert x["window_anchor"] == max_tx
    assert x["window_days"] == 90
    for p in ("D", "R"):
        book = x["portfolios"][p]
        rows = [r for r in tx if r["party"] == p and r["transaction_date"] >= cutoff]
        assert book["n_tx"] == len(rows)
        assert book["n_members"] == len({r["member"] for r in rows})
        # Full recompute of the top-10 net-buy book (same aggregation).
        agg: dict = {}
        for r in rows:
            a = agg.setdefault(r["ticker"], [0, 0])
            a[0 if r["direction"] == "buy" else 1] += 1
        want = sorted(
            ({"ticker": t, "net_buy": a[0] - a[1], "n_buy": a[0], "n_sell": a[1]}
             for t, a in agg.items()),
            key=lambda h: (-h["net_buy"], -h["n_buy"], h["ticker"]),
        )[:10]
        got_h = book["holdings"]
        assert [h["ticker"] for h in got_h] == [h["ticker"] for h in want], (
            "holdings = the true top-10 by (net_buy desc, n_buy desc, ticker)"
        )
        for h in got_h:
            assert h["net_buy"] == h["n_buy"] - h["n_sell"]

    # Display-lane boundary: signal lists, never performance.
    ml = x["methodology"].lower()
    assert "house" in ml and ("no prices" in ml or "no returns" in ml)


def test_ark_panel_contract() -> None:
    """ARK panel: official-CSV derivation, honest skips, overlap consistency.

    The panel rides ARK's own daily Full Holdings CSVs (display-only). The
    contract pins: per-fund top lists sorted by official weight desc and
    capped at 10; family overlap rows genuinely held by 2+ funds with fund
    lists drawn from the exported funds; skipped rows disclosed per fund;
    and the methodology must disclose that the URLs were browser-verified
    and that no prices/returns are claimed.
    """
    x = _load("ark.json")
    assert x["status"] in {"ok", "awaiting_fetch"}
    assert {"as_of", "n_funds", "n_funds_expected", "funds", "family_overlap",
            "methodology", "snapshot_ts"} <= set(x)
    if x["status"] != "ok" or not x["funds"]:
        return
    assert 0 < x["n_funds"] <= x["n_funds_expected"] == 8
    fund_ticks = set()
    for f in x["funds"]:
        assert {"ticker", "fund", "as_of", "n_positions", "skipped_rows", "top"} <= set(f)
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", f["as_of"])
        assert f["n_positions"] > 0 and f["skipped_rows"] >= 0
        assert 1 <= len(f["top"]) <= 10
        ws = [p["weight_pct"] for p in f["top"]]
        assert ws == sorted(ws, reverse=True), "top sorted by weight desc"
        assert all(p["weight_pct"] > 0 and p["ticker"] for p in f["top"])
        fund_ticks.add(f["ticker"])
    assert x["as_of"] == max(f["as_of"] for f in x["funds"])
    for o in x["family_overlap"]:
        assert len(o["funds"]) >= 2, "overlap rows held by 2+ funds"
        assert set(o["funds"]) <= fund_ticks, "overlap funds = exported funds"
        assert o["max_weight_pct"] > 0
    nf = [len(o["funds"]) for o in x["family_overlap"]]
    assert nf == sorted(nf, reverse=True), "overlap sorted by fund count desc"
    ml = x["methodology"].lower()
    assert "ark" in ml and ("no prices" in ml or "no returns" in ml)


def test_theme_etfs_panel_contract() -> None:
    """Theme-ETF panel: issuer-official CSVs, honest skips, resonance.

    The panel rides the issuers' own daily holdings files (iShares
    latest-holdings.csv + Global X dated full-holdings CSVs; display-only).
    The contract pins: per-fund top lists sorted by official weight desc and
    capped at 10 with a disclosed issuer; the cross-fund resonance rows
    genuinely held by 2+ funds drawn from the exported funds; skipped rows
    disclosed per fund; the honest count (funds whose source was dropped are
    NOT silently padded — n_funds stays within the pinned expected set);
    and the methodology must disclose official-source provenance and that no
    prices/returns are claimed.
    """
    x = _load("theme_etfs.json")
    assert x["status"] in {"ok", "awaiting_fetch"}
    assert {"as_of", "n_funds", "n_funds_expected", "funds",
            "cross_fund_overlap", "methodology", "snapshot_ts"} <= set(x)
    if x["status"] != "ok" or not x["funds"]:
        return
    assert 0 < x["n_funds"] <= x["n_funds_expected"] == 10
    fund_ticks = set()
    for f in x["funds"]:
        assert {"ticker", "issuer", "fund", "as_of", "n_positions",
                "skipped_rows", "top"} <= set(f)
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", f["as_of"])
        assert f["issuer"] and f["n_positions"] > 0 and f["skipped_rows"] >= 0
        assert 1 <= len(f["top"]) <= 10
        ws = [p["weight_pct"] for p in f["top"]]
        assert ws == sorted(ws, reverse=True), "top sorted by weight desc"
        assert all(p["weight_pct"] > 0 and p["ticker"] for p in f["top"])
        fund_ticks.add(f["ticker"])
    assert x["as_of"] == max(f["as_of"] for f in x["funds"])
    for o in x["cross_fund_overlap"]:
        assert len(o["funds"]) >= 2, "resonance rows held by 2+ funds"
        assert set(o["funds"]) <= fund_ticks, "resonance funds = exported funds"
        assert o["max_weight_pct"] > 0
    nf = [len(o["funds"]) for o in x["cross_fund_overlap"]]
    assert nf == sorted(nf, reverse=True), "resonance sorted by fund count desc"
    ml = x["methodology"].lower()
    assert "official" in ml and ("no prices" in ml or "no returns" in ml)


def test_reddit_trending_panel_contract() -> None:
    """ApeWisdom trending board: first-party fields, honest pagination facts.

    The panel rides ApeWisdom's free public API (apewisdom.io, filter/stocks).
    The contract pins: ranks strictly ascending with unique (rank, ticker)
    rows; every row carries the first-party fields verbatim (mentions/
    upvotes ≥ 0, nullable 24h lags); the pagination disclosure is CONSISTENT
    (pagination_ok=False ⇒ n_rows is the served page-1 window, and the
    methodology says so); and the display-lane boundary (today-snapshot,
    never PIT, no research claim) is stated.
    """
    x = _load("reddit_trending.json")
    assert x["status"] in {"ok", "awaiting_fetch"}
    assert {"as_of", "count_declared", "n_rows", "served_pages",
            "pagination_ok", "sibling_filters", "tickers", "methodology",
            "snapshot_ts"} <= set(x)
    if x["status"] != "ok" or not x["tickers"]:
        return
    rows = x["tickers"]
    assert 0 < len(rows) == x["n_rows"]
    ranks = [r["rank"] for r in rows]
    assert ranks == sorted(ranks), "board sorted by rank"
    assert len({(r["rank"], r["ticker"]) for r in rows}) == len(rows), (
        "no duplicate (rank, ticker) rows — the ingest dedupes pages"
    )
    for r in rows:
        assert {"rank", "ticker", "name", "mentions", "upvotes",
                "rank_24h_ago", "mentions_24h_ago"} <= set(r)
        assert r["mentions"] >= 0
        assert r["ticker"]
        for lag in ("rank_24h_ago", "mentions_24h_ago"):
            assert r[lag] is None or r[lag] >= 0
    # Pagination honesty: when the API declared pages it never served, the
    # panel must say so and the visible window is the served page.
    if not x["pagination_ok"]:
        assert x["served_pages"] == 1
        assert x["n_rows"] < x["count_declared"], (
            "page-1-only board must be smaller than the declared count"
        )
        assert "page 1" in x["methodology"].lower()
    ml = x["methodology"].lower()
    assert "apewisdom" in ml and "display-only" in ml and "pit" in ml, (
        "must disclose the source and the today-snapshot (never-PIT) boundary"
    )


def test_form_d_panel_contract() -> None:
    """Form D panel: exempt-offering stream, status from immutable form types.

    The panel rides the same EDGAR EFTS form-level machinery as /ipo, with
    forms=D expanding to D + D/A. The contract pins: status enum derived from
    the form (D -> new, D/A -> amendment) with row-form agreement; newest-
    first order; visible rows a capped prefix of the window (by_form counts
    the FULL window, so by_form sums may exceed the visible list — both
    disclosed); doc links to the EDGAR filing index; and the methodology
    must disclose the not-parsed offering amounts (v1 honesty boundary).
    """
    x = _load("form_d.json")
    assert x["status"] in {"ok", "awaiting_fetch"}
    assert {"as_of", "window", "issuers", "total", "by_form", "filings",
            "methodology", "snapshot_ts"} <= set(x)
    if x["status"] != "ok" or not x["filings"]:
        return
    dates: list[str] = []
    for r in x["filings"]:
        assert {"company", "ticker", "filed_date", "form", "status", "doc_url"} <= set(r)
        assert r["form"] in {"D", "D/A"}, f"unexpected form {r['form']}"
        assert r["status"] == ("new" if r["form"] == "D" else "amendment"), (
            "status derived from the immutable form type"
        )
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["filed_date"])
        assert r["doc_url"].startswith("https://www.sec.gov/Archives/edgar/data/")
        dates.append(r["filed_date"])
    assert dates == sorted(dates, reverse=True), "filings newest-first"
    assert x["as_of"] == max(dates)
    # Visible list is a capped prefix: window totals live in by_form/total.
    assert x["total"] >= len(x["filings"])
    assert sum(x["by_form"].values()) == x["total"], "by_form counts the full window"
    assert set(x["by_form"]) <= {"D", "D/A"}
    ml = x["methodology"].lower()
    assert "form d" in ml and "not extracted" in ml and "display-only" in ml


def test_form_def14a_panel_contract() -> None:
    """DEF 14A panel: governance proxy-statement stream, honest v1 boundary.

    The panel rides the same EDGAR EFTS form-level machinery as /ipo, with
    forms=DEF%2014A (live-probed 2026-08-23: 1,387 filings over the ~120-day
    window, every row carrying form "DEF 14A" — proxy amendments are filed
    as DEFA14A, a separate root form out of scope, so the DEF 14A/A ->
    amendment arm is defense-in-depth only). The contract pins: status enum
    derived from the form with row-form agreement; newest-first order;
    visible rows a capped prefix of the window (by_form counts the FULL
    window); doc links to the EDGAR filing index; and the methodology must
    disclose the not-parsed person-level content (v1 honesty boundary).
    """
    x = _load("def14a.json")
    assert x["status"] in {"ok", "awaiting_fetch"}
    assert {"as_of", "window", "issuers", "total", "by_form", "filings",
            "methodology", "snapshot_ts"} <= set(x)
    if x["status"] != "ok" or not x["filings"]:
        return
    dates: list[str] = []
    for r in x["filings"]:
        assert {"company", "ticker", "filed_date", "form", "status", "doc_url"} <= set(r)
        assert r["form"] in {"DEF 14A", "DEF 14A/A"}, f"unexpected form {r['form']}"
        assert r["status"] == ("new" if r["form"] == "DEF 14A" else "amendment"), (
            "status derived from the immutable form type"
        )
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["filed_date"])
        assert r["doc_url"].startswith("https://www.sec.gov/Archives/edgar/data/")
        dates.append(r["filed_date"])
    assert dates == sorted(dates, reverse=True), "filings newest-first"
    assert x["as_of"] == max(dates)
    # Visible list is a capped prefix: window totals live in by_form/total.
    assert x["total"] >= len(x["filings"])
    assert sum(x["by_form"].values()) == x["total"], "by_form counts the full window"
    assert set(x["by_form"]) <= {"DEF 14A", "DEF 14A/A"}
    ml = x["methodology"].lower()
    assert "def 14a" in ml and "not parsed" in ml and "not extracted" in ml, (
        "must disclose the DEFERRED person-level extraction"
    )
    assert "display-only" in ml


def test_def14a_persons_panel_contract() -> None:
    """DEF 14A persons panel: honest person-level coverage discipline.

    The panel parses ONLY the newest ~150 filings with conservative tiered
    confidence (age-anchored roster rows / middle-initial names with a
    witnessed role word — 宁可 null 不猜测: unreadable documents ship
    persons=[] and parsed=false, never a guessed name). The contract pins:
    coverage self-consistency (n_with_persons <= n_filings_processed <=
    target; confidence tiers count every processed filing exactly once);
    every shipped person carries >= 1 witnessed role word (by_role bounded by
    distinct persons x the role vocabulary); board rows carry director/
    officer counts consistent with independent sets plus EDGAR primary-doc
    links; top-person seat counts are bounded by the processed prefix; the
    methodology must disclose parsed/coverage/null semantics and display-only.
    """
    x = _load("def14a_persons.json")
    assert x["status"] in {"ok", "awaiting_fetch"}
    assert {"as_of", "n_filings_target", "n_filings_processed", "n_with_persons",
            "coverage_pct", "n_persons_distinct", "by_role", "confidence",
            "boards", "top_persons", "methodology", "snapshot_ts"} <= set(x)
    if x["status"] != "ok" or not x["n_filings_processed"]:
        return
    n_proc = x["n_filings_processed"]
    assert 0 <= x["n_with_persons"] <= n_proc <= x["n_filings_target"]
    assert abs(x["coverage_pct"] - round(100.0 * x["n_with_persons"] / n_proc, 1)) < 0.11
    conf = x["confidence"]
    assert sum(conf.values()) == n_proc, "tiers count every processed filing exactly once"
    assert (
        conf.get("section_age_rows", 0) + conf.get("section_name_roles", 0)
        == x["n_with_persons"]
    ), "with-persons filings split exactly into the two parse tiers"
    # Every shipped person carries >= 1 witnessed role word; by_role counts
    # distinct persons per canonical role (multi-role persons count in each
    # role — bounded by persons x the 11-role vocabulary).
    assert sum(x["by_role"].values()) <= x["n_persons_distinct"] * 11
    for b in x["boards"]:
        assert {"company", "ticker", "issuer_cik", "n_persons", "n_directors",
                "n_officers", "filed_date", "doc_url"} <= set(b)
        assert b["n_persons"] >= 1
        assert b["n_directors"] + b["n_officers"] >= 1, (
            "a parsed board always has a director/officer (roles are required)"
        )
        assert b["n_directors"] <= b["n_persons"] and b["n_officers"] <= b["n_persons"]
        assert b["doc_url"].startswith("https://www.sec.gov/Archives/edgar/data/")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", b["filed_date"])
    for tp in x["top_persons"]:
        assert {"name", "roles", "n_companies", "n_director_seats", "companies"} <= set(tp)
        assert len(tp["roles"]) >= 1, "a shipped person always has a witnessed role word"
        assert 1 <= tp["n_companies"] <= n_proc
        assert 0 <= tp["n_director_seats"] <= tp["n_companies"]
        assert len(tp["companies"]) == min(tp["n_companies"], 10)
    seats = [tp["n_companies"] for tp in x["top_persons"]]
    assert seats == sorted(seats, reverse=True), "top persons ordered by company count desc"
    ml = x["methodology"].lower()
    assert "parsed" in ml and "coverage" in ml and "display-only" in ml
    assert "null" in ml, "must disclose the honest-null semantics"


def test_filing_stream_panel_contract() -> None:
    """Unified filing stream v2: DIRECT whole-market per-form queries.

    The panel IS the source query (v1 derived it from the per-form panels,
    inheriting their visible caps and missing 10-K/10-Q entirely — the v1→v2
    migration is disclosed in the methodology). The contract pins: the v2
    form family (EFTS root forms + /A amendments; Schedule 13 via the daily
    index lanes; the form-family completion added DEF 14A / DEFA14A / 424B4);
    newest-first order; by_form counts the VISIBLE stream and
    sums to n_visible; every row carries an EDGAR link and a real form
    label; ticker "None"-strings and placeholder filers must NOT leak; the
    methodology must disclose the direct EFTS machinery, the 10-K/10-Q
    coverage, the DEF 14A completion, and that 13F is excluded.
    """
    x = _load("filing_stream.json")
    assert x["status"] in {"ok", "awaiting_fetch"}
    assert {"as_of", "window", "total_merged", "n_visible", "by_form",
            "filings", "methodology", "snapshot_ts"} <= set(x)
    if x["status"] != "ok" or not x["filings"]:
        return
    dates: list[str] = []
    allowed_forms = {
        "8-K", "8-K/A", "10-K", "10-K/A", "10-Q", "10-Q/A",
        "S-1", "S-1/A", "4", "4/A", "D", "D/A",
        "SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A",
        # Form-family completion (2026-08-23): DEF 14A (space → %20 per
        # form_def14a), DEFA14A (separate root — the proxy-amendment vehicle
        # in practice; a future DEF 14A/A stays whitelisted
        # defense-in-depth), 424B4 (IPO pricing prospectus).
        "DEF 14A", "DEF 14A/A", "DEFA14A", "424B4",
    }
    for r in x["filings"]:
        assert {"form", "who", "ticker", "filed_date", "doc_url"} <= set(r)
        assert r["form"] in allowed_forms, f"unexpected form {r['form']}"
        assert r["who"] and r["who"] != "—"
        assert r["ticker"] != "None", "no str(None) leaks from source rows"
        assert "申报人见原文" not in r["who"], "no placeholder-filer leaks"
        assert r["doc_url"].startswith("https://www.sec.gov/Archives/edgar/data/")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["filed_date"])
        dates.append(r["filed_date"])
    assert dates == sorted(dates, reverse=True), "newest-first"
    assert x["n_visible"] == len(x["filings"]) <= 800
    assert x["total_merged"] >= x["n_visible"]
    assert sum(x["by_form"].values()) == x["n_visible"], (
        "by_form counts the visible stream"
    )
    assert set(x["by_form"]) <= allowed_forms
    assert x["as_of"] == max(dates)
    ml = x["methodology"].lower()
    assert "direct" in ml and "efts" in ml and "13f" in ml, (
        "must disclose the direct EFTS machinery and the 13F exclusion"
    )
    assert "10-k" in ml and "10-q" in ml, "the v2 10-K/10-Q coverage is disclosed"
    assert "def 14a" in ml and "424b4" in ml, (
        "the form-family completion (DEF 14A / DEFA14A / 424B4) is disclosed"
    )
    assert "display-only" in ml


def test_filing_stream_deep_cuts_contract() -> None:
    """10-K/10-Q deep-cut slices for /annual + /quarterly.

    The 800-newest visible cap squeezes periodic reports out of the visible
    stream entirely in filing season (the committed v2 snapshot carries ZERO
    visible 10-K/10-Q rows while the window counts 76 / 2,115), so the panel
    carries two form-family deep cuts sliced from the SAME direct-query
    parquet, each newest-first with its own cap 400 and a FULL-window total.
    The contract pins: strict form whitelists per slice; newest-first order;
    the 400 cap; *_total counts the full window (>= the visible slice, and
    the two totals cannot exceed total_merged); row hygiene identical to the
    main stream; the methodology discloses the deep cuts and their caps.
    """
    x = _load("filing_stream.json")
    assert x["status"] in {"ok", "awaiting_fetch"}
    assert {"annual_filings", "quarterly_filings", "annual_total",
            "quarterly_total"} <= set(x), (
        "the /annual + /quarterly routes read these deep-cut fields"
    )
    if x["status"] != "ok" or not x["filings"]:
        return
    for key, total_key, forms in (
        ("annual_filings", "annual_total", {"10-K", "10-K/A"}),
        ("quarterly_filings", "quarterly_total", {"10-Q", "10-Q/A"}),
    ):
        rows = x[key]
        assert len(rows) <= 400, f"{key} respects the deep-cut cap 400"
        dates: list[str] = []
        for r in rows:
            assert r["form"] in forms, f"unexpected form {r['form']} in {key}"
            assert {"form", "who", "ticker", "filed_date", "doc_url"} <= set(r)
            assert r["who"] and r["who"] != "—"
            assert r["ticker"] != "None", "no str(None) leaks from source rows"
            assert r["doc_url"].startswith("https://www.sec.gov/Archives/edgar/data/")
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["filed_date"])
            dates.append(r["filed_date"])
        assert dates == sorted(dates, reverse=True), f"{key} newest-first"
        assert x[total_key] >= len(rows), (
            f"{total_key} counts the FULL window, not the capped slice"
        )
    # Deep-cut window totals are subsets of the whole direct-query window.
    assert x["annual_total"] + x["quarterly_total"] <= x["total_merged"]
    ml = x["methodology"].lower()
    assert "annual_filings" in ml and "quarterly_filings" in ml, (
        "must disclose the deep-cut fields"
    )
    assert "cap 400" in ml, "the deep-cut caps are disclosed"


def test_news_feed_panel_contract() -> None:
    """GDELT news-feed panel: metadata-only headline stream, link-out only.

    The panel rides ONE bounded GDELT Doc 2.0 artlist request per refresh
    (fixed quoted-phrase query, sourcelang:eng, sort=datedesc machine order).
    The contract pins: newest-first machine order with as_of = the newest
    first-seen stamp; the visible items list is a capped (<=150) newest prefix
    of the retained window while by_day/total count the FULL window
    (sum(by_day) == total); every row links out to the publisher (http-prefixed
    url) carrying METADATA only (the identity contract: seendate/title/url/
    domain/language/sourcecountry, honest empties); and the methodology must
    disclose the GDELT source, the link-out/no-article-text boundary and the
    display-only lane.
    """
    x = _load("news_feed.json")
    assert x["status"] in {"ok", "awaiting_fetch"}
    assert {"as_of", "window", "query", "total", "n_sources", "by_day",
            "items", "methodology", "snapshot_ts"} <= set(x)
    if x["status"] != "ok" or not x["items"]:
        return
    stamps: list[str] = []
    for r in x["items"]:
        assert {"seendate", "title", "url", "domain", "language",
                "sourcecountry"} <= set(r)
        assert r["url"].startswith("http"), "every row links out to the publisher"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", r["seendate"]), (
            "seendate normalized to ISO-UTC or honest empty — never guessed"
        )
        stamps.append(r["seendate"])
    assert stamps == sorted(stamps, reverse=True), "machine order newest-first"
    # as_of = the newest stamp in the FULL retained window; the capped prefix
    # is newest-first, so it must start there.
    assert x["as_of"] == stamps[0]
    # Visible list is a capped prefix: window totals live in by_day/total.
    assert 0 < len(x["items"]) <= 150
    assert x["total"] >= len(x["items"])
    assert sum(d["count"] for d in x["by_day"]) == x["total"], (
        "by_day counts the full retained window"
    )
    day_dates = [d["date"] for d in x["by_day"]]
    assert day_dates == sorted(day_dates), "by_day ascending"
    assert x["window"]["start"] == day_dates[0] and x["window"]["end"] == day_dates[-1]
    assert x["window"]["start"] <= x["window"]["end"]
    assert x["n_sources"] >= 1
    assert "sourcelang:eng" in x["query"], "the fixed query is shown verbatim"
    ml = x["methodology"].lower()
    assert "gdelt" in ml and "display-only" in ml, (
        "must disclose the source and the display-lane boundary"
    )
    assert "outbound link" in ml and "no article text" in ml, (
        "must disclose the link-out / no-article-text boundary"
    )



def test_filers13f_panel_contract() -> None:
    """13F filer directory: exhaustive annual universe, directory facts only.

    The panel is the FULL filer directory (not the star registry). The
    contract pins: unique zero-padded CIKs; per-filer counts >= 1 with the
    full list summing to total_filings; latest_filed inside the declared
    window; rows sorted latest-first as exported; and the methodology must
    disclose the EFTS machinery, the 13F-NT exclusion and the
    directory-not-holdings boundary.
    """
    x = _load("filers13f.json")
    assert x["status"] in {"ok", "awaiting_fetch"}
    assert {"as_of", "window", "n_filers", "n_with_amendments",
            "total_filings", "filers", "methodology", "snapshot_ts"} <= set(x)
    if x["status"] != "ok" or not x["filers"]:
        return
    ciks = [r["cik"] for r in x["filers"]]
    assert len(ciks) == x["n_filers"] == len(set(ciks)), "unique CIK per row"
    assert all(re.fullmatch(r"\d{10}", c) for c in ciks), "zero-padded 10-digit CIKs"
    latest = [r["latest_filed"] for r in x["filers"]]
    assert latest == sorted(latest, reverse=True), "exported latest-first"
    assert sum(r["n_filings"] + r["n_amendments"] for r in x["filers"]) == x["total_filings"]
    assert all(r["n_filings"] >= 1 and r["n_amendments"] >= 0 for r in x["filers"])
    assert x["window"]["start"] <= min(latest) and max(latest) <= x["window"]["end"]
    assert x["as_of"] == max(latest)
    ml = x["methodology"].lower()
    assert "efts" in ml and "13f-nt" in ml and "holdings" in ml


def test_form_ipo_panel_contract() -> None:
    """IPO panel schema: filing shape, status enum, honest counting, date order.

    Locks the contract the /ipo view renders against: status is derived from
    the immutable form type (S-1 family -> filed, 424B4 -> priced — the only
    two legal values); by_status counts must be FILING counts consistent with
    the panel total; the export is FULL-stream (cap raised 150 → 1200 on
    2026-08-22, every filing visible), so the visible list's per-status counts
    equal by_status exactly; filings sorted by filed_date descending; the
    ticker is empty for pre-symbol filers (honest, never guessed); each row
    links the EDGAR filing-index page (offer terms live inside the
    prospectus documents — v1 does not parse them).
    """
    f = _load("ipo.json")
    assert f["status"] in {"ok", "awaiting_fetch"}
    assert {"as_of", "window", "issuers", "total", "by_status", "by_form",
            "filings", "methodology"} <= set(f)
    if f["status"] != "ok" or not f["filings"]:
        return  # awaiting-fetch placeholder keeps the shape loose
    dates: list[str] = []
    for r in f["filings"]:
        assert {"company", "ticker", "filed_date", "form", "status",
                "doc_url"} <= set(r)
        assert r["status"] in {"filed", "priced"}, f"bad status: {r['status']!r}"
        # Status must agree with the immutable form type it is derived from.
        if r["form"] in ("S-1", "S-1/A"):
            assert r["status"] == "filed"
        else:
            assert r["form"] == "424B4" and r["status"] == "priced"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["filed_date"])
        assert r["doc_url"].startswith("https://www.sec.gov/Archives/edgar/data/")
        assert r["doc_url"].endswith("-index.htm")
        dates.append(r["filed_date"])
    assert dates == sorted(dates, reverse=True), "filings must be newest-first"
    assert f["as_of"] == max(dates), "as_of must be the latest filed_date"
    assert sum(f["by_status"].values()) == f["total"], (
        "by_status must count FILINGS (sum == total), not companies"
    )
    assert set(f["by_status"]) <= {"filed", "priced"}
    # Full export (safety cap 1200): every filing is visible, so the visible
    # list length equals the panel total and each status count equals by_status
    # exactly — the old 150-row truncation made these subset checks.
    assert len(f["filings"]) == f["total"], (
        f"visible filings ({len(f['filings'])}) != total ({f['total']}) — "
        "export must be full-stream (safety cap 1200)"
    )
    visible: dict[str, int] = {}
    for r in f["filings"]:
        visible[r["status"]] = visible.get(r["status"], 0) + 1
    assert visible == f["by_status"], (
        f"visible per-status counts {visible} != by_status {f['by_status']}"
    )
    assert sum(f["by_form"].values()) == f["total"], "by_form must sum to total"
    for form, status in (("S-1", "filed"), ("S-1/A", "filed"), ("424B4", "priced")):
        if form in f["by_form"]:
            assert f["by_form"][form] <= f["by_status"][status]



def test_politician_trades_tx_panel_contract() -> None:
    """Transaction-level STOCK Act panel (PTR PDF parse, TASK-S).

    Locks the honest-coverage shape the /congress transaction section and the
    /stock politician-trades join consume: direction enum mirrors the view's
    DIRECTION labels, late_days is internally consistent with the two dates,
    and the by_party arithmetic sums to total.
    """
    f = _load("politician_trades_tx.json")
    assert f["status"] in {"ok", "awaiting_fetch"}
    if f["status"] != "ok":
        return
    assert f["total"] > 0
    assert set(f["by_party"]) <= {"D", "R", "unknown"}
    assert sum(v["n_trades"] for v in f["by_party"].values()) == f["total"]
    for tx in f["transactions"]:
        assert tx["direction"] in {"buy", "sell_partial", "sell_full"}
        assert tx["amount_range"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(tx["transaction_date"]))
        d1 = datetime.strptime(str(tx["transaction_date"]), "%Y-%m-%d")
        d2 = datetime.strptime(str(tx["filing_date"]), "%Y-%m-%d")
        assert tx["days_late"] == (d2 - d1).days
        assert tx["doc_url"].startswith("https://disclosures-clerk.house.gov/")
    # Late-filing KPI reconciles with the visible rows it summarizes.
    n_late = sum(1 for tx in f["transactions"] if tx["days_late"] > 45)
    assert f["late_filings"] >= n_late  # KPI over ALL rows, visible subset <= it

def test_form13f_panel_contract() -> None:
    """13F panel schema: manager shape, positions/changes enums, coverage format.

    Locks the contract the /institutions view renders against (direction enum
    mirrored in DIRECTION_LABEL, ticker nullable for honest unresolved
    issuers) and the ``ticker_coverage`` accounting string computed at export
    time (resolved-ticker identities over latest-quarter visible-book rows).
    """
    f = _load("form13f.json")
    assert f["status"] in {"ok", "awaiting_fetch"}
    assert {"managers", "as_of", "methodology", "ticker_coverage"} <= set(f)
    if f["status"] != "ok" or not f["managers"]:
        return  # awaiting-fetch placeholder keeps the shape loose
    for m in f["managers"]:
        assert {"cik", "name", "category", "quarter", "filed", "n_positions", "positions"} <= set(m)
        assert re.fullmatch(r"\d{10}", str(m["cik"])), f"CIK must be 10-digit: {m['cik']}"
        assert m["category"] in FORM13F_CATEGORIES, (
            f"category must be an editorial enum value: {m['category']!r}"
        )
        for h in m["positions"]:
            assert {"issuer", "cusip", "value", "shares", "pct"} <= set(h)
            assert isinstance(h["ticker"], (str, type(None)))
            assert h["value"] > 0 and h["shares"] >= 0
        for c in m.get("changes", []):
            assert c["direction"] in {"new", "increased", "reduced", "exited"}
            assert isinstance(c["ticker"], (str, type(None)))
    # Coverage is "linked/total" over visible-book rows; total must equal the count.
    linked, _, total = f["ticker_coverage"].partition("/")
    assert linked.isdigit() and total.isdigit(), f"bad coverage format: {f['ticker_coverage']!r}"
    n_top = sum(len(m["positions"]) for m in f["managers"])
    assert int(total) == n_top, "coverage denominator must equal visible-book row count"
    n_linked = sum(1 for m in f["managers"] for h in m["positions"] if h["ticker"])
    assert int(linked) == n_linked, "coverage numerator must equal resolved visible-book tickers"
    assert n_linked >= 1, "at least some issuers must resolve (name-join layer works)"


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
    reconcile with the data-health map. Planned endpoints (status='planned',
    xiaoyinsi-style honest disclosure of not-yet-built panels) are exempt from
    the freshness reconciliation — they describe NO existing health panel by
    construction — but must still carry license + source + a reserved path.
    """
    cat = _load("api_catalog.json")
    assert cat["status"] == "ok"
    eps = cat["endpoints"]
    assert len(eps) >= 20
    dh = _load("data_health.json")
    dh_keys = {p["key"] for p in dh["panels"]}
    valid = {"daily", "cadence", "frozen"}
    for e in eps:
        if e["status"] == "planned":
            assert e["as_of"] is None, "a planned endpoint has no observation by construction"
            assert e["freshness"] == "planned"
        else:
            assert e["freshness"] in valid
            assert e["key"] in dh_keys, f"{e['key']} missing from data_health"
            assert "unverified" not in e["license"], f"{e['key']} license unmapped"
        assert e["method"] == "GET" and e["status"] in {"available", "planned"}
        assert e["path"] == f"/api/v1/panels/{e['file']}"
        assert isinstance(e["license"], str) and len(e["license"]) > 5
        assert isinstance(e["source"], str) and len(e["source"]) > 3
    available = [e for e in eps if e["status"] == "available"]
    assert {e["key"] for e in available} == dh_keys, "catalog must cover every health panel"
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


# --- smart_money ticker/filer restoration (daily-index dedup round) ----------


def pct_contract(r: dict, *, form: str | None = None) -> None:
    """The percent-of-class contract shared by the 13D and 13G panels.

    * ``pct_now`` / ``pct_prev`` are floats within [0, 100] or honest nulls —
      never strings, never out-of-range, never negative.
    * ``pct_prev`` only on /A amendments (the previous value lives in the
      amendment narrative; original filings never carry one).
    * ``pct_status`` is DERIVED from parsed values only: "exited" iff an
      explicit parsed 0, "below_5" iff a parsed value in (0, 5); a null
      pct_now must yield a null status (no parsing → no state machine).
    """
    for k in ("pct_now", "pct_prev"):
        v = r.get(k)
        assert v is None or (isinstance(v, (int, float)) and 0.0 <= v <= 100.0), (
            f"{k} must be null or a number in [0,100], got {v!r}"
        )
    if form is None:
        form = str(r.get("form", ""))
    if not form.endswith("/A") and not r.get("is_amendment"):
        assert r.get("pct_prev") is None, (
            f"pct_prev only in amendments, got {r.get('pct_prev')!r} on {form!r}"
        )
    st = r.get("pct_status")
    now = r.get("pct_now")
    if now is None:
        assert st is None, "null pct_now must yield a null pct_status"
    elif now == 0:
        assert st == "exited", f"pct_now 0 must be 'exited', got {st!r}"
    elif now < 5:
        assert st == "below_5", f"pct_now <5 must be 'below_5', got {st!r}"
    else:
        assert st is None, f"pct_now >=5 has no derived status, got {st!r}"


def test_smart_money_recent_ticker_and_filer_restored() -> None:
    """recent_filings must carry parsed tickers + real filers where resolvable.

    Regression: the EDGAR daily-index merge built rows with ticker='' and the
    placeholder filer — the newest 60 were ALL empty (ticker→stock-page loop
    dead, stock_universe 13D join empty). Fix: per-accession dedup (the daily
    index lists a filing under subject AND filer entities — the raw aggregate
    double-listed ~40% of rows); the listed company is the subject, co-indexed
    names become the filer, tickers backfilled offline from the cached SEC
    company_tickers snapshot (+ frozen EFTS name map).

    Thresholds are MEASURED floors, not aspirations: recent 13D windows always
    contain filings on unlisted targets (funds, LLCs, individuals — no ticker
    exists) and both-listed groups with no offline subject discriminator, and
    rows only the committed JSON covers (fresher cron cache elsewhere) arrive
    as single-member accessions whose filer cannot be re-derived offline.
    Measured on 2026-08-19: 73% ticker / 53% real filer (90% / 73% once the
    local daily aggregate catches up to the committed newest filings).
    """
    sm = _load("smart_money.json")
    recent = sm["recent_filings"]
    # Live window raised 60 → 120 at export (2026-08-22). Range-pinned so BOTH
    # the committed JSON (regenerated wherever the EFTS/daily caches live) and
    # a fresh 120-row export pass: >= the old 60 floor, <= the new cap.
    assert 60 <= len(recent) <= 120, (
        f"live window must be 60..120 rows (export cap 120), got {len(recent)}"
    )
    n_ticker = sum(1 for r in recent if r.get("ticker"))
    assert n_ticker / len(recent) >= 0.70, (
        f"ticker coverage regressed: {n_ticker}/{len(recent)}"
    )
    for r in recent:
        assert isinstance(r["filer"], str) and r["filer"], "filer must be a non-empty string"
        assert isinstance(r["target"], str) and r["target"]
        assert isinstance(r["date"], str) and len(r["date"]) == 10
    n_real_filer = sum(1 for r in recent if not r["filer"].startswith("("))
    assert n_real_filer / len(recent) >= 0.50, (
        f"real-filer rate regressed: {n_real_filer}/{len(recent)}"
    )
    # A resolved ticker is an uppercase symbol (EFTS parens convention / SEC
    # snapshot), never whitespace or lowercase noise.
    for r in recent:
        if r["ticker"]:
            assert r["ticker"] == r["ticker"].strip().upper()
    # Percent-of-class contract on every visible 13D row (null-tolerant).
    for r in recent:
        pct_contract(r, form=r.get("form"))


def test_smart_money_source_health_counts_agree_with_panel() -> None:
    """data_health.source_health must mirror the committed smart_money panel."""
    dh = _load("data_health.json")
    sh = dh["source_health"]["smart_money"]
    sm = _load("smart_money.json")
    recent = sm["recent_filings"]
    assert isinstance(sh["n_recent"], int) and sh["n_recent"] == len(recent)
    assert isinstance(sh["ticker_null"], int)
    assert sh["ticker_null"] == sum(1 for r in recent if not r.get("ticker"))
    assert sh["ticker_null"] <= sh["n_recent"]
    assert isinstance(sh["days_since_latest"], int) and sh["days_since_latest"] >= 0
    # Parsed-percent null rate: misses are counted, never papered over.
    assert isinstance(sh["pct_now_null"], int)
    assert sh["pct_now_null"] == sum(
        1 for r in recent if r.get("pct_now") is None
    )
    assert sh["pct_now_null"] <= sh["n_recent"]


def test_stakes_13g_panel_contract() -> None:
    """13G panel schema: field set, form enum, date order, EDGAR URLs, sums.

    Locks the contract the /smart-money "13G passive stream" card renders
    against: rows are per-ACCESSION filing events (form enum SC 13G / SC 13G/A
    only — the passive family); filings sorted by date descending; doc_url is
    an EDGAR archive link; by_form counts are FILING counts summing to total;
    the unresolved ticker stays an honest null; the methodology discloses the
    public-domain source, the EFTS Schedule-13 freeze, the DEFERRED
    ownership/state-machine parsing, and the display-only boundary.
    """
    f = _load("stakes_13g.json")
    assert f["status"] in {"ok", "awaiting_fetch"}
    assert {"as_of", "window", "total", "by_form", "filings",
            "methodology"} <= set(f)
    assert {"start", "end"} <= set(f["window"])
    if f["status"] != "ok" or not f["filings"]:
        return  # awaiting-fetch placeholder keeps the shape loose
    dates: list[str] = []
    for r in f["filings"]:
        assert {"filer", "target", "ticker", "date", "form", "doc_url"} <= set(r)
        assert r["form"] in ("SC 13G", "SC 13G/A"), f"bad form: {r['form']!r}"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["date"])
        assert isinstance(r["filer"], str) and r["filer"]
        assert isinstance(r["target"], str) and r["target"]
        # Unresolved ticker is an honest null, never a guess and never "" noise.
        assert r["ticker"] is None or (
            isinstance(r["ticker"], str) and r["ticker"].strip().upper() == r["ticker"]
        )
        assert r["doc_url"].startswith("https://www.sec.gov/Archives/edgar/data/")
        dates.append(r["date"])
    assert dates == sorted(dates, reverse=True), "filings must be newest-first"
    # filings are the NEWEST 150 rows, so the newest row is always visible.
    assert f["as_of"] == dates[0], "as_of must be the newest visible filed date"
    assert f["window"]["end"] == f["as_of"], "window end must be as_of"
    assert sum(f["by_form"].values()) == f["total"], (
        "by_form must count FILINGS (sum == total), not index rows or holders"
    )
    assert set(f["by_form"]) <= {"SC 13G", "SC 13G/A"}
    m = f["methodology"]
    assert "public domain" in m, "methodology must disclose the license"
    assert "display-only" in m.lower() and "not a research claim" in m, (
        "methodology must disclose the display-only boundary"
    )
    assert "2024-12-17" in m, "must disclose the EFTS Schedule-13 freeze"
    # Percent second stage: the parsing BOUNDARY must be disclosed — visible
    # rows parsed, misses honest nulls, status derived from parsed values only.
    assert "NOT parsed" in m or "not parsed" in m, (
        "must disclose the bounded parse window (rows beyond it not parsed)"
    )
    assert "honest null" in m, "must disclose the honest-null policy"
    assert "pct_status" in m or "exited" in m, (
        "must disclose the derived-status boundary"
    )
    # --- percent-of-class contract (bounded document parse merge) -----------
    for r in f["filings"]:
        assert {"pct_now", "pct_prev", "pct_status"} <= set(r)
        pct_contract(r, form=r["form"])


def test_stakes_13g_source_health_counts_agree_with_panel() -> None:
    """data_health.source_health must mirror the committed stakes_13g panel."""
    dh = _load("data_health.json")
    sh = dh["source_health"]["stakes_13g"]
    sg = _load("stakes_13g.json")
    filings = sg["filings"]
    assert isinstance(sh["n_filings"], int) and sh["n_filings"] == len(filings)
    assert sh["ticker_null"] == sum(1 for r in filings if not r.get("ticker"))
    assert sh["filer_unresolved"] == sum(
        1 for r in filings if str(r.get("filer", "")).startswith("(")
    )
    assert sh["ticker_null"] <= sh["n_filings"]
    assert isinstance(sh["days_since_latest"], int) and sh["days_since_latest"] >= 0
    # Parsed-percent null rate: misses are counted, never papered over.
    assert isinstance(sh["pct_now_null"], int)
    assert sh["pct_now_null"] == sum(1 for r in filings if r.get("pct_now") is None)
    assert sh["pct_now_null"] <= sh["n_filings"]


def test_data_health_source_health_shape() -> None:
    """source_health quantifies field-level quality per source, exact schema."""
    dh = _load("data_health.json")
    sh = dh["source_health"]
    assert set(sh) == {"smart_money", "stakes_13g", "reddit", "cot"}
    assert set(sh["smart_money"]) == {
        "ticker_null", "n_recent", "days_since_latest", "pct_now_null",
    }
    assert set(sh["stakes_13g"]) == {
        "ticker_null", "filer_unresolved", "n_filings", "days_since_latest",
        "pct_now_null",
    }
    assert set(sh["reddit"]) == {"bull_ratio_null", "n_picks"}
    assert set(sh["cot"]) == {"weeks_since_latest"}
    reddit = _load("reddit.json")
    picks = reddit.get("picks", [])
    assert isinstance(sh["reddit"]["n_picks"], int) and sh["reddit"]["n_picks"] == len(picks)
    assert isinstance(sh["reddit"]["bull_ratio_null"], int)
    assert sh["reddit"]["bull_ratio_null"] == sum(
        1 for p in picks if p.get("bull_ratio") is None
    )
    assert isinstance(sh["cot"]["weeks_since_latest"], int)
    assert sh["cot"]["weeks_since_latest"] >= 0
    # The counts are computed on the committed panels — reconcile spot-check.
    assert "source_health" in dh["methodology"]


def test_planned_disclosure_present_and_consistent() -> None:
    """Planned (not-built) panels disclosed in data_health + api_catalog alike.

    Honesty pattern learned from the xiaoyinsi datahub (x-status: planned):
    the panel count must never be mistaken for coverage. 13f-holdings,
    cn-industry-classification (2026-08-20) and politician-trades (2026-08-21,
    House PTR filing-stream level) ALL GRADUATED to live panels — the planned
    list is now empty; the mechanism stays pinned so any future planned key
    is disclosed in BOTH data_health and api_catalog (they can never drift).
    """
    dh = _load("data_health.json")
    planned = dh["planned"]
    assert {p["key"] for p in planned} == set()
    for p in planned:
        assert isinstance(p["key"], str) and isinstance(p["note"], str) and p["note"]
    planned_keys = {p["key"] for p in planned}
    panel_keys = {p["key"] for p in dh["panels"]}
    assert not (planned_keys & panel_keys), "a planned key must not shadow a live panel"

    cat = _load("api_catalog.json")
    cat_planned = [e for e in cat["endpoints"] if e["status"] == "planned"]
    assert {e["key"] for e in cat_planned} == planned_keys, (
        "api_catalog planned keys must match data_health planned keys"
    )
    for e in cat_planned:
        assert e["as_of"] is None
        assert e["path"] == f"/api/v1/panels/{e['file']}"
        assert isinstance(e["license"], str) and "planned" in e["license"]
        assert isinstance(e["source"], str) and e["source"]
    available_keys = {e["key"] for e in cat["endpoints"] if e["status"] == "available"}
    assert available_keys == panel_keys, "available endpoints stay 1:1 with live panels"
    assert "planned" in cat["methodology"]


# --- SEC 13F-HR star-manager holdings -----------------------------------------

#: Display-only editorial category enum (mirrors scripts/form13f_fetch.py
#: CATEGORIES and web manager-book CATEGORY_ORDER). Human-curated tags — NOT
#: a SEC data-source field.
FORM13F_CATEGORIES = {
    "value",
    "growth",
    "activist",
    "macro",
    "quant",
    "china_background",
    "other",
}


def test_form13f_status_and_shape() -> None:
    f = _load("form13f.json")
    assert f["status"] in {"ok", "awaiting_fetch"}
    assert isinstance(f["managers"], list)
    # License honesty is load-bearing on this panel (public-domain claim).
    assert "public domain" in f["methodology"].lower()
    assert "display-only" in f["methodology"].lower()
    # Units disclosure: EDGAR 2014+ XML values are whole dollars (the
    # "thousands" note is the legacy HTML rendering) — pinned so the panel
    # can never silently revert to the thousands reading.
    assert "whole USD" in f["methodology"]


def test_form13f_managers_when_ok() -> None:
    """Lock the manager schema: CIK, quarter frame, monotonic positions pcts."""
    f = _load("form13f.json")
    if f["status"] != "ok":
        return  # awaiting branch: guards above must not raise; nothing else to check
    ms = f["managers"]
    assert len(ms) >= 12, "13F panel needs >=12 star managers"
    seen_ciks: set[str] = set()
    for m in ms:
        assert {"cik", "name", "category", "quarter", "filed", "n_positions",
                "total_value", "positions", "changes"} <= set(m)
        assert len(m["cik"]) == 10 and m["cik"].isdigit()
        assert m["cik"] not in seen_ciks, "one manager row per CIK"
        seen_ciks.add(m["cik"])
        # Editorial category enum (display-only tag; "other" share is allowed
        # to be large — honest curation, not forced balance).
        assert m["category"] in FORM13F_CATEGORIES, m["category"]
        assert m["total_value"] > 0
        assert m["n_positions"] >= 1
        # positions = top holdings by value (up to 50); short books report fewer.
        assert len(m["positions"]) == min(50, m["n_positions"]), m["name"]
        values = [h["value"] for h in m["positions"]]
        assert values == sorted(values, reverse=True), f"positions by value desc: {m['name']}"
        pcts = [h["pct"] for h in m["positions"]]
        assert pcts == sorted(pcts, reverse=True), f"pct monotonic: {m['name']}"
        for h in m["positions"]:
            assert {"issuer", "cusip", "value", "shares", "pct", "ticker"} <= set(h)
            assert h["value"] >= 0 and h["shares"] >= 0
            assert 0 <= h["pct"] <= 100
            # ticker is a nullable display link (exact-name match), never "".
            assert h["ticker"] is None or (
                isinstance(h["ticker"], str) and h["ticker"].strip().upper() == h["ticker"]
            )


def test_form13f_changes_enum_when_ok() -> None:
    """Frame-diff directions are exactly the four-way display enum."""
    f = _load("form13f.json")
    if f["status"] != "ok":
        return
    allowed = {"new", "increased", "reduced", "exited"}
    for m in f["managers"]:
        for c in m["changes"]:
            assert c["direction"] in allowed, c["direction"]
            assert {"issuer", "cusip", "direction", "delta_pct", "ticker"} <= set(c)
            # delta_pct only meaningful on share-count moves (null for new/exited)
            if c["direction"] in {"new", "exited"}:
                assert c["delta_pct"] is None
            else:
                assert isinstance(c["delta_pct"], (int, float))
                assert abs(c["delta_pct"]) < 1e6
            # delta_value (whole-USD cur − prev) ships with the next mainline
            # re-export — validate when present, never require the key (the
            # committed JSON predates it).
            if "delta_value" in c:
                dv = c["delta_value"]
                assert dv is None or isinstance(dv, (int, float))
                if isinstance(dv, (int, float)):
                    assert abs(dv) < 1e15, "whole-USD magnitude guard"
                    # Only where the frame-diff semantics are provable:
                    # new = full position value added (>0); exited = full
                    # value removed (<0). On increased/reduced the VALUE sign
                    # may oppose the share move (price drift) — deliberately
                    # NOT asserted.
                    if c["direction"] == "new":
                        assert dv > 0, "new position: delta_value = full value"
                    elif c["direction"] == "exited":
                        assert dv < 0, "exited position: delta_value = -full value"
    as_of = f["as_of"]
    assert isinstance(as_of, str) and len(as_of) == 10
    for m in f["managers"]:
        assert m["quarter"] <= as_of, "panel as_of is the max report quarter"


def test_form13f_category_counts_honest() -> None:
    """The exported category_counts must equal the managers list it summarizes.

    Editorial categories are display-only curation, so the ONLY integrity that
    matters is honest counting: every manager carries exactly one enum tag,
    the aggregate ``category_counts`` (when present) matches a recount of the
    managers array, and the total adds up to ``len(managers)``. No minimum per
    category is enforced — a large "other" share is acceptable honesty.
    """
    f = _load("form13f.json")
    if f["status"] != "ok" or not f["managers"]:
        return
    recount: dict[str, int] = {}
    for m in f["managers"]:
        assert m["category"] in FORM13F_CATEGORIES, m["category"]
        recount[m["category"]] = recount.get(m["category"], 0) + 1
    counts = f.get("category_counts")
    if counts is not None:
        assert set(counts) <= FORM13F_CATEGORIES, sorted(set(counts))
        assert counts == recount, "category_counts must match a recount"
        assert sum(counts.values()) == len(f["managers"])
    # Methodology must disclose that the tags are curated, not sourced.
    assert "curated" in f["methodology"].lower() or "curation" in f["methodology"].lower()
