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


def test_sector_breakdown_methodology_discloses_unclassified() -> None:
    """A-share sectors are not in the listing file → 'Unclassified' bucket.
    The methodology string must disclose this honestly (not hide it)."""
    sb = _load("sector_breakdown.json")
    if sb["status"] != "ok":
        return
    assert "Unclassified" in sb["methodology"] or "unclassified" in sb["methodology"].lower()
