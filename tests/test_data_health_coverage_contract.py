"""TASK-H2 — web consumption surface <-> data_health manifest full coverage.

P0-3③ institutionalization. Background: the R1A round nearly shipped
score_diagnostics without its data_health/api_catalog registration — a panel
missing from the manifest is INVISIBLE on the data-health map, the API catalog
and the atlas freshness disclosure. The producer-side registry lives in
scripts/export_terminal_data.py::_DATA_HEALTH_MANIFEST; the api_catalog <->
data_health key parity is already pinned (test_web_terminal_data.py). This
module pins the LAST link, both directions:

1. every panel JSON the web terminal consumes (the index.ts `aionis` barrel +
   the dedicated heavy modules) has a data_health.panels row with the pinned
   category;
2. every data_health.panels row resolves to a JSON file the terminal actually
   ships and imports (anti-ghost-row);
3. the six atlas-consumed panels (metrics / ic_monthly / calibration_reliability
   / score_diagnostics / data_health / api_catalog) are present and dated.

Hermetic by construction: pure checks over tracked repo artifacts — no network,
no runs/ or data/ dependency, zero skips, zero xfails.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AIONIS_DATA = ROOT / "web" / "src" / "data" / "aionis"
ATLAS_DIR = ROOT / "web" / "src" / "components" / "atlas"
ATLAS_PAGE = ROOT / "web" / "src" / "app" / "(dashboard)" / "atlas" / "page.tsx"

# data_health key -> (web consumer, json file, category).
#
# 新增面板必须同步此表 — a new panel must update THREE places in the same
# commit: (1) scripts/export_terminal_data.py::_DATA_HEALTH_MANIFEST (producer
# registry), (2) the web consumption surface — either the index.ts `aionis`
# barrel or a dedicated heavy module in web/src/data/aionis/, and (3) THIS
# table. `consumer` is the exact camelCase barrel member for barrel panels, or
# the dedicated module filename (*.ts) for the deliberately-unmerged heavy
# panels. Row order mirrors _DATA_HEALTH_MANIFEST for reviewable diffs.
EXPECTED_PANELS: dict[str, tuple[str, str, str]] = {
    # --- frozen: derived from frozen OOS artifacts (ledger #49 lineage) ---
    "metrics": ("metrics", "metrics.json", "frozen"),
    "picks": ("picks", "picks.json", "frozen"),
    "shorts": ("shorts", "shorts.json", "frozen"),
    "picks_meta": ("picksMeta", "picks_meta.json", "frozen"),
    "sector_breakdown": ("sectorBreakdown", "sector_breakdown.json", "frozen"),
    "picks_backtest": ("picksBacktest", "picks_backtest.json", "frozen"),
    "ic_monthly": ("icMonthly", "ic_monthly.json", "frozen"),
    "score_diagnostics": ("scoreDiagnostics", "score_diagnostics.json", "frozen"),
    # P1-6 R1-full — decile monotonicity (frozen score surface + frozen panels;
    # display-lane derivation, zero-clock).
    "ic_deciles": ("icDeciles", "ic_deciles.json", "frozen"),
    # Round-31 H1 panel (ledger-derived horizon sweep summary; frozen — static
    # until a new sweep appends an exploratory row).
    "horizon_robustness": ("horizonRobustness", "horizon_robustness.json", "frozen"),
    # Round-H4 model card (frozen run artifacts + tracked headline, hash-pinned;
    # zero-clock — changes only when the frozen artifacts themselves do).
    "model_card": ("modelCard", "model_card.json", "frozen"),
    # Round-H5 model inventory (ledger × frozen-dir reconciliation; frozen —
    # zero-clock, moves only when the tracked ledger or the frozen run dirs do).
    "model_inventory": ("modelInventory", "model_inventory.json", "frozen"),
    "pick_conviction": ("pickConviction", "pick_conviction.json", "frozen"),
    "model_health": ("modelHealth", "model_health.json", "frozen"),
    "calibration_reliability": (
        "calibrationReliability",
        "calibration_reliability.json",
        "frozen",
    ),
    "power_floor": ("powerFloor", "power_floor.json", "frozen"),
    "sigma_survey": ("sigmaSurvey", "sigma_survey.json", "frozen"),
    "bps_sweep": ("bpsSweep", "bps_sweep.json", "frozen"),
    "evidence": ("evidence", "evidence.json", "frozen"),
    "stock_universe": ("stock-universe.ts", "stock_universe.json", "frozen"),
    # --- daily: recomputed by the CI refresh from live caches ---
    "themes": ("themes", "themes.json", "daily"),
    "theme_signals": ("themeSignals", "theme_signals.json", "daily"),
    "market_context": ("marketContext", "market_context.json", "daily"),
    "macro_drivers": ("macroDrivers", "macro_drivers.json", "daily"),
    "taco": ("taco", "taco.json", "daily"),
    "form4": ("form4", "form4.json", "daily"),
    "form8k": ("form8k", "form8k.json", "daily"),
    "news_feed": ("newsFeed", "news_feed.json", "daily"),
    "executives": ("executives", "executives.json", "daily"),
    "ipo": ("ipo", "ipo.json", "daily"),
    "form_d": ("formD", "form_d.json", "daily"),
    # NOTE the key mismatch: health key `form_def14a`, barrel member `def14a`.
    "form_def14a": ("def14a", "def14a.json", "daily"),
    "def14a_persons": ("def14aPersons", "def14a_persons.json", "daily"),
    "filing_stream": ("filingStream", "filing_stream.json", "daily"),
    "politician_trades": ("politicianTrades", "politician_trades.json", "daily"),
    "politician_trades_tx": (
        "politicianTradesTx",
        "politician_trades_tx.json",
        "daily",
    ),
    "party_index": ("partyIndex", "party_index.json", "daily"),
    "lineage_graph": ("lineage-graph.ts", "lineage_graph.json", "daily"),
    "reddit": ("reddit", "reddit.json", "daily"),
    "reddit_trending": ("redditTrending", "reddit_trending.json", "daily"),
    "headline_provenance": (
        "headlineProvenance",
        "headline_provenance.json",
        "daily",
    ),
    "ledger_audit": ("ledgerAudit", "ledger_audit.json", "daily"),
    "stakes_13g": ("stakes13g", "stakes_13g.json", "daily"),
    "ark": ("ark", "ark.json", "daily"),
    "theme_etfs": ("themeEtfs", "theme_etfs.json", "daily"),
    # --- cadence: advances on the source's own publication rhythm ---
    "freight_taco": ("freightTaco", "freight_taco.json", "cadence"),
    "companies_dir": ("companies-dir.ts", "companies_dir.json", "cadence"),
    "korea_proxy": ("koreaProxy", "korea_proxy.json", "cadence"),
    "cot": ("cot", "cot.json", "cadence"),
    "smart_money": ("smartMoney", "smart_money.json", "cadence"),
    "form13f": ("form13f.ts", "form13f.json", "cadence"),
    "form13f_stars": ("form13f-stars.ts", "form13f-stars.json", "cadence"),
    "filers13f": ("filers13f.ts", "filers13f.json", "cadence"),
    "knowledge_shelf": ("knowledgeShelf", "knowledge_shelf.json", "cadence"),
    "evidence_matrix": ("evidenceMatrix", "evidence_matrix.json", "cadence"),
    "provider_vintage": ("providerVintage", "provider_vintage.json", "cadence"),
}

# Barrel members that ARE the registries themselves: consumed by the atlas,
# deliberately NOT rows in data_health.panels (a manifest row for the manifest
# inside the manifest would be self-referential).
META_BARREL: dict[str, str] = {
    "dataHealth": "data_health.json",
    "apiCatalog": "api_catalog.json",
}

# The six panels /atlas (page + components) consumes directly, as barrel keys.
ATLAS_BARREL_KEYS = {
    "metrics",
    "icMonthly",
    "calibrationReliability",
    "scoreDiagnostics",
    "icDeciles",  # P1-6 R1-full decile monotonicity block (round 62)
    "dataHealth",
    "apiCatalog",
}

_BARREL_BLOCK = re.compile(r"export const aionis = \{\n(.*?)\n\};", re.DOTALL)
_JSON_IMPORT = re.compile(r'^import\s+(\w+)\s+from\s+"\./([\w-]+\.json)";$', re.M)
_MEMBER_START = re.compile(r"^ {2}([A-Za-z_]\w*):(.*)$")
_JSON_IDENT = re.compile(r"\b(\w+Json)\b")
_JSON_CONSUMED = re.compile(r'from\s+"\./([\w-]+\.json)"')
_AIONIS_MEMBER = re.compile(r"\baionis\.(\w+)")


def _load(name: str) -> dict:
    return json.loads((AIONIS_DATA / name).read_text(encoding="utf-8"))


def _health_rows() -> dict[str, dict]:
    dh = _load("data_health.json")
    return {p["key"]: p for p in dh["panels"]}


def _parse_barrel() -> dict[str, str]:
    """Parse index.ts: `aionis` member key -> imported json filename."""
    text = (AIONIS_DATA / "index.ts").read_text(encoding="utf-8")
    idents = dict(_JSON_IMPORT.findall(text))
    block = _BARREL_BLOCK.search(text)
    assert block is not None, (
        "web/src/data/aionis/index.ts: `export const aionis = {` block not "
        "found — the barrel layout changed, update the TASK-H2 parser"
    )
    chunks: list[tuple[str, list[str]]] = []
    for line in block.group(1).splitlines():
        m = _MEMBER_START.match(line)
        if m:  # member lines sit at exactly 2-space indent
            chunks.append((m.group(1), [m.group(2)]))
        elif chunks:
            chunks[-1][1].append(line)
    members: dict[str, str] = {}
    for key, lines in chunks:
        jm = _JSON_IDENT.search("\n".join(lines))
        assert jm is not None, f"barrel member {key!r}: no *Json reference found"
        ident = jm.group(1)
        assert ident in idents, (
            f"barrel member {key!r}: {ident} has no `import {ident} from ...` line"
        )
        members[key] = idents[ident]
    assert members, "barrel parse produced no members — index.ts layout changed"
    return members


def _all_consumed_json() -> dict[str, set[str]]:
    """Every JSON imported by any data module: file -> importing module names."""
    out: dict[str, set[str]] = {}
    for ts in sorted(AIONIS_DATA.glob("*.ts")):
        for fname in _JSON_CONSUMED.findall(ts.read_text(encoding="utf-8")):
            out.setdefault(fname, set()).add(ts.name)
    return out


def _atlas_consumed_members() -> set[str]:
    files = [ATLAS_PAGE, *sorted(ATLAS_DIR.glob("*.tsx"))]
    consumed: set[str] = set()
    for f in files:
        consumed |= set(_AIONIS_MEMBER.findall(f.read_text(encoding="utf-8")))
    return consumed


# --- 1. the hardcoded table IS the data_health.panels row set -----------------


def test_expected_table_is_the_full_health_manifest() -> None:
    """Exact two-sided key equality + per-key (file, category) match + summary
    reconciliation. The table above is the documentation of the coverage
    contract; this test keeps it from drifting in either direction."""
    dh = _load("data_health.json")
    rows = {p["key"]: p for p in dh["panels"]}
    missing = sorted(set(EXPECTED_PANELS) - set(rows))
    extra = sorted(set(rows) - set(EXPECTED_PANELS))
    assert not missing and not extra, (
        f"data_health.panels drifted from the TASK-H2 table: "
        f"rows missing from the table {missing}; stale table keys {extra}. "
        "Sync the table (and index.ts + _DATA_HEALTH_MANIFEST)."
    )
    for key, (_consumer, fname, category) in EXPECTED_PANELS.items():
        row = rows[key]
        assert row["file"] == fname, f"{key}: manifest file drift"
        assert row["category"] == category, (
            f"{key}: category drift — {row['category']!r} != pinned {category!r}"
        )
    s = dh["summary"]
    assert s["n_panels"] == len(rows) == len(EXPECTED_PANELS)
    for category, count in (
        ("frozen", s["n_frozen"]),
        ("daily", s["n_daily"]),
        ("cadence", s["n_cadence"]),
    ):
        n = sum(1 for c in EXPECTED_PANELS.values() if c[2] == category)
        assert count == n, f"summary n_{category}={count} != table count {n}"


# --- 2. the barrel cannot drift from the table --------------------------------


def test_barrel_members_sync_with_expected_table() -> None:
    """Every index.ts `aionis` member is either an EXPECTED_PANELS consumer or
    a META registry, and each member's imported file matches the table. A new
    barrel member without a table row (the R1A near-miss shape) fails here."""
    actual = _parse_barrel()
    expected: dict[str, str] = dict(META_BARREL)
    for consumer, fname, _category in EXPECTED_PANELS.values():
        if not consumer.endswith(".ts"):
            expected[consumer] = fname
    unregistered = sorted(set(actual) - set(expected))
    stale = sorted(set(expected) - set(actual))
    assert not unregistered and not stale, (
        f"index.ts aionis object drifted from the TASK-H2 table: "
        f"unregistered barrel members {unregistered}; stale table rows {stale}. "
        "新增面板必须同步此表 (index.ts barrel + EXPECTED_PANELS + "
        "exporter _DATA_HEALTH_MANIFEST)."
    )
    for member, fname in actual.items():
        assert expected[member] == fname, (
            f"barrel member {member} now imports {fname}, table pins "
            f"{expected[member]} — resync the table"
        )


# --- 3. reflexive anti-ghost-row ----------------------------------------------


def test_every_health_row_points_at_a_real_file() -> None:
    """Each data_health.panels key must resolve to an existing JSON in
    web/src/data/aionis/ with present=true — a row describing a file the
    terminal does not ship is a phantom freshness disclosure."""
    for key, row in _health_rows().items():
        assert row["present"] is True, f"{key}: manifest claims present=false"
        assert (AIONIS_DATA / row["file"]).is_file(), (
            f"{key}: ghost row — {row['file']} does not exist in "
            "web/src/data/aionis/"
        )


def test_no_unregistered_consumed_json() -> None:
    """Closure in the reverse direction: the JSON files imported by the data
    modules (barrel + dedicated heavy modules) equal the manifest files plus
    the two registry files. A new module importing an unregistered JSON is the
    module-path twin of the R1A near-miss and fails here; an orphan row
    (manifest file nothing imports) fails too."""
    consumed = _all_consumed_json()
    registered = {row["file"] for row in _health_rows().values()}
    registered |= set(META_BARREL.values())
    unregistered = sorted(set(consumed) - registered)
    orphaned = sorted(registered - set(consumed))
    assert not unregistered, (
        f"JSON imported by web/src/data/aionis/*.ts but missing from "
        f"data_health.panels: {unregistered} (imported by "
        f"{ {f: sorted(consumed[f]) for f in unregistered} })"
    )
    assert not orphaned, (
        f"data_health.panels files no data module imports (orphan rows): "
        f"{orphaned}"
    )


# --- 4. atlas consumption surface ---------------------------------------------


def test_atlas_consumes_exactly_the_six_pinned_panels() -> None:
    """Pin /atlas's direct consumption: the page + components read exactly the
    six barrel members below — nothing else, nothing missing. A new
    aionis.* reference inside the atlas must be added here AND to
    EXPECTED_PANELS (when it introduces a new panel)."""
    assert ATLAS_PAGE.is_file(), "atlas page moved — update ATLAS_PAGE"
    components = sorted(ATLAS_DIR.glob("*.tsx"))
    assert components, "atlas components moved — update ATLAS_DIR"
    consumed = _atlas_consumed_members()
    assert consumed == ATLAS_BARREL_KEYS, (
        f"atlas consumption surface drifted: got {sorted(consumed)}, pinned "
        f"{sorted(ATLAS_BARREL_KEYS)}"
    )


def test_atlas_row_panels_present_and_dated() -> None:
    """The row-backed atlas panels: present=true with a live observation date.

    as_of semantics per panel (mirrors _dh_as_of in the exporter): metrics ->
    latest_month; ic_monthly / score_diagnostics -> the LAST row's month (rows
    sort month-first, so the tail row is the newest observation)."""
    rows = _health_rows()
    metrics = _load("metrics.json")
    assert rows["metrics"]["present"] is True
    assert rows["metrics"]["as_of"] == metrics["latest_month"]
    for key in ("ic_monthly", "score_diagnostics"):
        payload = _load(f"{key}.json")
        newest = payload[-1]["month"]
        assert newest == max(r["month"] for r in payload), (
            f"{key}: tail row must carry the newest month"
        )
        assert rows[key]["present"] is True
        assert rows[key]["as_of"] == newest, (
            f"{key}: manifest as_of must be the last row's month"
        )
    # FLIPPED (round-32 integration): calibration_reliability is datable from
    # its own payload — the exporter now derives as_of = max(last month per
    # region series). The TASK-H2 KNOWN-GAP (as_of=None) is closed.
    cr_row = rows["calibration_reliability"]
    assert cr_row["present"] is True
    cr = _load("calibration_reliability.json")
    series_months = [r["series"][-1]["month"] for r in cr["regions"].values()]
    assert all(series_months), (
        "the panel carries datable per-region series — as_of must track them"
    )
    assert cr_row["as_of"] == max(series_months), (
        "calibration_reliability manifest as_of must be the newest series month"
    )


def test_atlas_meta_panels_self_describing() -> None:
    """data_health.json and api_catalog.json are the registries themselves:
    deliberately NOT rows in data_health.panels (self-reference), and their
    as_of semantics is their own snapshot_ts export stamp (non-empty)."""
    rows = _health_rows()
    assert "data_health" not in rows and "api_catalog" not in rows, (
        "the registries must not list themselves as panels"
    )
    dh = _load("data_health.json")
    cat = _load("api_catalog.json")
    assert dh["status"] == "ok" and dh["snapshot_ts"]
    assert cat["status"] == "ok" and cat["snapshot_ts"]
