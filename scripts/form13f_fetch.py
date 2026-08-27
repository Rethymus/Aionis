"""Bounded 13F-HR star-manager holdings fetch (display-only, exploratory).

40 celebrity institutional managers × the 2 most recent DISTINCT report
quarters (the second quarter exists purely for the quarter-over-quarter frame
diff shown in the /institutions panel and /manager/[cik] detail pages). NOT
the ~9,000-filer full 13F universe — scope is deliberately bounded and polite.

All CIKs below were verified live against EDGAR (full-text-search JSON over
13F-HR filings + the submissions JSON) on 2026-08-22: entity name + a recent
13F-HR filing. Candidates that could NOT be verified as actively filing were
honestly dropped (see the exclusion log in the task report): Scion Asset
Management, Greenlight Capital (last 13F-HR 2024-02), Omega Advisors, Pabrai
Investment Funds, Glenpoint. Politeness: >=2s host spacing via ``_policy_get``;
every response cached idempotently under ``data/cache/`` so reruns make zero
HTTP calls.

``category`` is EDITORIAL curation (value / growth / activist / macro / quant /
china_background / other) — a display-layer tag written here, in this fetch
list, NOT a field that exists in any SEC data source. It flows into the
aggregate and the exported JSON for the /institutions category filter.

Writes ``data/cache/form13f_aggregate.parquet`` (gitignored, regenerable) —
one row per (manager, quarter, issuer line):
``[cik, manager_name, zh_name, category, quarter, filing_date, accession,
form, issuer, title_class, cusip, value_usd, shares, option_type]``.

Incremental design (per-manager checkpoint, mirroring scripts/form4_fetch.py):
each completed manager is merged into the aggregate and written to disk
IMMEDIATELY — a mid-run timeout preserves every manager already finished. A
rerun re-fetches all managers from warm cache (zero HTTP) and rewrites the
same rows (idempotent), or picks up cleanly from where it stopped.

Usage (from the repo root)::

    uv run python scripts/form13f_fetch.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from aionis.ingest.form13f import fetch_manager_holdings

#: Display-only editorial categories for the /institutions filter (mirrored in
#: web/src/data/aionis/index.ts Form13fManager.category consumers and
#: tests/test_web_terminal_data.py). NOT a SEC data-source field.
CATEGORIES = (
    "value",
    "growth",
    "activist",
    "macro",
    "quant",
    "china_background",
    "other",
)

# Star-manager registry — CIKs verified against EDGAR on 2026-08-22 (see
# module docstring). CIK -> (EDGAR entity name, zh display name, category).
# zh_name is display-layer only (the panel's optional Chinese label; the view
# tolerates null — use null when no conventional Chinese name is established).
MANAGERS: dict[int, tuple[str, str | None, str]] = {
    # --- the original 12 (verified 2026-08-20) --------------------------------
    1067983: ("BERKSHIRE HATHAWAY INC", "伯克希尔·哈撒韦（巴菲特）", "value"),
    1350694: ("Bridgewater Associates, LP", "桥水基金（达利欧）", "macro"),
    1697748: ("ARK Investment Management LLC", "ARK 投资（伍德）", "growth"),
    1759760: ("H&H International Investment, LLC", "H&H 国际投资（段永平）", "china_background"),
    1709323: ("Himalaya Capital Management LLC", "喜马拉雅资本（李录）", "china_background"),
    1336528: ("Pershing Square Capital Management, L.P.", "潘兴广场（阿克曼）", "activist"),
    1167483: ("TIGER GLOBAL MANAGEMENT LLC", "老虎环球（科尔曼）", "growth"),
    1656456: ("Appaloosa LP", "Appaloosa（泰珀）", "value"),
    1135730: ("COATUE MANAGEMENT LLC", "蔻图资本", "growth"),
    1103804: ("VIKING GLOBAL INVESTORS LP", "Viking 全球投资（哈尔夫）", "growth"),
    1647251: ("TCI Fund Management Ltd", "TCI 基金（霍恩）", "activist"),
    1037389: ("RENAISSANCE TECHNOLOGIES LLC", "文艺复兴科技（西蒙斯）", "quant"),
    # --- +28 added 2026-08-22 (FTS-verified, active 13F-HR filers) ------------
    1029160: ("SOROS FUND MANAGEMENT LLC", "索罗斯基金管理（索罗斯）", "macro"),
    1536411: ("Duquesne Family Office LLC", "杜肯家族办公室（德鲁肯米勒）", "macro"),
    1040273: ("Third Point LLC", "Third Point（勒布）", "activist"),
    1418814: ("ValueAct Holdings, L.P.", "ValueAct（乌本）", "activist"),
    1061165: ("LONE PINE CAPITAL LLC", "独松资本（曼德尔）", "growth"),
    934639: ("MAVERICK CAPITAL LTD", "小牛资本（安斯利）", "growth"),
    1020066: ("SANDS CAPITAL MANAGEMENT, LLC", "Sands 资本", "growth"),
    1720792: ("Ruane, Cunniff & Goldfarb L.P.", "瑞安·坎尼夫（红杉基金）", "value"),
    1325447: ("First Eagle Investment Management, LLC", "天鹰资本（First Eagle）", "value"),
    1217541: ("Diamond Hill Capital Management, LLC", "钻石山资本", "value"),
    1135778: ("MILLER VALUE PARTNERS, LLC", "米勒价值合伙（比尔·米勒）", "value"),
    949509: ("OAKTREE CAPITAL MANAGEMENT LP", "橡树资本（马克斯）", "other"),
    1762304: ("HHLR ADVISORS, LTD.", "高瓴 HHLR（张磊）", "china_background"),
    1848138: (
        "Greenwoods Asset Management Hong Kong Ltd.",
        "景林资产（蒋锦志）",
        "china_background",
    ),
    1791786: ("Elliott Investment Management L.P.", "埃利奥特（辛格）", "activist"),
    1061768: ("BAUPOST GROUP LLC/MA/", "Baupost（克拉曼）", "value"),
    1179392: ("TWO SIGMA INVESTMENTS, LP", "两西格玛（Two Sigma）", "quant"),
    1009207: ("D. E. Shaw & Co., Inc.", "D.E. Shaw（肖）", "quant"),
    1167557: ("AQR CAPITAL MANAGEMENT LLC", "AQR 资本（阿斯内斯）", "quant"),
    1273087: ("MILLENNIUM MANAGEMENT LLC", "千禧管理（英格兰）", "quant"),
    1423053: ("CITADEL ADVISORS LLC", "城堡投资（格里芬）", "quant"),
    1603466: ("Point72 Asset Management, L.P.", "Point72（科恩）", "other"),
    2051323: ("CAXTON ASSOCIATES LLP", "卡克斯顿（Caxton）", "macro"),
    1517137: ("Starboard Value LP", "Starboard Value（史密斯）", "activist"),
    1056831: ("FAIRHOLME CAPITAL MANAGEMENT LLC", "费尔霍姆（伯克维茨）", "value"),
    807985: ("SOUTHEASTERN ASSET MANAGEMENT INC/TN/", "东南资产管理（霍金斯）", "value"),
    1138995: ("GLENVIEW CAPITAL MANAGEMENT, LLC", "格伦维尤资本（罗宾斯）", "growth"),
    1448574: ("MOORE CAPITAL MANAGEMENT, LP", "摩尔资本（培根）", "macro"),
    # --- +2 admitted 2026-08-27 (TASK-DISP-F; six-gate curation bar PASS,
    # evidence: reports/design/2026-08-26-stars-candidates-evidence.json;
    # names verbatim from data.sec.gov submissions) ---------------------------
    1535472: ("Corvex Management LP", None, "activist"),
    807249: ("GAMCO INVESTORS, INC. ET AL", "GAMCO（加贝利）", "value"),
}

QUARTERS = 2  # latest report quarter + previous (frame diff needs both)
OUT = Path("data/cache/form13f_aggregate.parquet")


def _assert_registry_sane() -> None:
    """Fail fast on a hand-edit that breaks the registry contract."""
    for cik, (name, zh, cat) in MANAGERS.items():
        assert cat in CATEGORIES, f"unknown category {cat!r} for {name} (CIK {cik})"
        assert isinstance(zh, (str, type(None))), f"zh_name must be str|None: {name}"
    assert len(MANAGERS) == len({m[0] for m in MANAGERS.values()}), "duplicate EDGAR name"


def _replace_manager_rows(
    running: pd.DataFrame | None, cik: int, new: pd.DataFrame
) -> pd.DataFrame:
    """Swap in ``new`` as the ONLY rows for ``cik`` (idempotent checkpoint merge).

    ``fetch_manager_holdings`` returns the 2 most recent quarters for the
    manager — a complete, self-contained slice — so replacing (not appending)
    keeps reruns bit-stable and prevents stale quarters from lingering when a
    manager's window slides forward. Rows for every OTHER manager pass through
    untouched (their own checkpoint iteration owns them).
    """
    if running is None or running.empty:
        return new.copy()
    kept = running[running["cik"] != int(cik)]
    return pd.concat([kept, new], ignore_index=True)


def main() -> None:
    _assert_registry_sane()
    # Seed the running aggregate with the previous run's output so a rerun
    # (warm cache) or a resume (cold crash) starts from what is already on
    # disk; every completed manager below is written through immediately.
    running = pd.read_parquet(OUT) if OUT.exists() else None
    if running is not None and not running.empty:
        print(
            f"[form13f-fetch] seeded running aggregate: {len(running)} rows, "
            f"{running['cik'].nunique()} managers",
            flush=True,
        )

    for i, (cik, (name, zh, cat)) in enumerate(MANAGERS.items(), 1):
        print(f"[form13f-fetch] ({i}/{len(MANAGERS)}) {name} (CIK {cik:010d})", flush=True)
        df = fetch_manager_holdings(cik, name, quarters=QUARTERS)
        if df.empty:
            print("  -> 0 holdings (graceful skip; manager excluded)", flush=True)
            continue
        df["zh_name"] = zh
        df["category"] = cat
        quarters_found = sorted(df["quarter"].unique(), reverse=True)
        latest = df[df["quarter"] == quarters_found[0]]
        print(
            f"  -> {len(df)} rows across {len(quarters_found)} quarter(s) "
            f"({', '.join(quarters_found)}); latest: {len(latest)} positions, "
            f"${latest['value_usd'].sum() / 1e9:,.2f}B",
            flush=True,
        )
        # Per-manager write-through: a timeout mid-run preserves every manager
        # already merged (incremental pattern borrowed from form4_fetch).
        running = _replace_manager_rows(running, cik, df)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        running.to_parquet(OUT, index=False)
        print(
            f"[form13f-fetch] checkpoint: {len(running)} rows, "
            f"{running['cik'].nunique()} managers -> {OUT}",
            flush=True,
        )

    if running is None or running.empty:
        print("[form13f-fetch] no holdings across managers; nothing written", flush=True)
        return

    # Drop managers that vanished from the registry (honest shrink, never a
    # silent leftover) and report the category mix for the record.
    running = running[running["cik"].isin(MANAGERS)]
    running.to_parquet(OUT, index=False)
    latest_quarter = running["quarter"].max()
    n_latest = len(running[running["quarter"] == latest_quarter])
    cat_mix = running.drop_duplicates("cik")["category"].value_counts().to_dict()
    print(
        f"[form13f-fetch] final: {len(running)} rows, {running['cik'].nunique()} "
        f"managers, latest quarter {latest_quarter} ({n_latest} positions); "
        f"categories {cat_mix} -> {OUT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
