"""Bounded House PTR TRANSACTION-level fetch (display-only, exploratory).

v2 of the STOCK Act lane (owner D4 "align granularity" gate): parses the
transaction table out of the PTR PDFs the filing-stream panel links to —
ported from the salvage branch ``agent/politician`` (0b7867a/70f8ad2, live-
verified 813 trades / 42 members on 2026-08-22). Per row: owner / asset /
ticker / asset class / buy vs sell(partial|full) / statutory $ band /
transacted + notified dates. Late-filing days (45-day STOCK Act clock) are
computed against the bulk-index FilingDate.

Honest counting, never silent drops: every date-pair+$ anchor is a row
CANDIDATE; ``candidates - parsed`` is the parse-failure count (scanned
image PDFs with no text layer are counted separately). Both land in
``data/cache/politician_trades_tx_stats.json`` and the panel.

Bounds: >=2s host spacing via the shared HTTP policy; PDFs cached per DocID
(the cache IS the resume mechanism — a rerun replays cached PDFs with zero
HTTP); hard wall-clock deadline (default 60 min) stops the run cleanly with
a partial, honest report.

Usage::

    # 1) sample first (parser may have drifted since 2026-08-22):
    uv run python scripts/politician_trades_tx_fetch.py --limit 20 --dump-text 3
    # 2) full year:
    uv run python scripts/politician_trades_tx_fetch.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aionis.ingest.politician_trades import (  # noqa: E402
    _doc_id_from_url,
    _cache_dir,
    extract_ptr_text,
    fetch_house_directory,
    fetch_house_ptr_year,
    fetch_ptr_pdf,
    parse_ptr_transactions,
)

OUT = Path("data/cache/politician_trades_tx.parquet")
STATS = Path("data/cache/politician_trades_tx_stats.json")
DUMP_DIR = Path("data/cache/ptr_text_dump")


def _norm_date(s: str | None) -> pd.Timestamp | None:
    return pd.Timestamp(s) if s else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument(
        "--limit", type=int, default=None,
        help="process only N evenly-spaced filings (sample verification mode)",
    )
    ap.add_argument(
        "--dump-text", type=int, default=0,
        help="write extracted text of the first K processed PDFs for inspection",
    )
    ap.add_argument(
        "--minutes", type=float, default=60.0,
        help="hard wall-clock budget; the run stops cleanly (cache resumable)",
    )
    args = ap.parse_args()

    deadline = time.monotonic() + args.minutes * 60

    filings = fetch_house_ptr_year(args.year)
    directory = fetch_house_directory()
    print(
        f"[ptr-tx-fetch] {args.year}: {len(filings)} PTR filings; "
        f"directory {len(directory)} members",
        flush=True,
    )
    if args.limit and args.limit < len(filings):
        step = len(filings) // args.limit
        filings = filings.sort_values("filing_date", na_position="last").reset_index(drop=True)
        filings = filings.iloc[::step].head(args.limit).reset_index(drop=True)
        print(f"[ptr-tx-fetch] SAMPLE: {len(filings)} evenly-spaced filings", flush=True)

    rows: list[dict] = []
    stats = {
        "year": args.year,
        "filings_total": int(len(filings)),
        "filings_processed": 0,
        "pdfs_http": 0,
        "pdfs_cached": 0,
        "no_text_pdfs": [],
        "fetch_errors": [],
        "row_candidates": 0,
        "rows_parsed": 0,
        "rows_excluded": 0,
        "complete": False,
    }

    for i, f in enumerate(filings.itertuples(index=False), 1):
        if time.monotonic() > deadline:
            print(
                f"[ptr-tx-fetch] DEADLINE hit at filing {i - 1}/{len(filings)} "
                f"— partial written, PDF cache resumable on rerun",
                flush=True,
            )
            break
        doc_url = str(f.doc_url)
        _, doc_id = _doc_id_from_url(doc_url)
        cache_fp = _cache_dir() / f"house_ptr_pdf_{args.year}_{doc_id}.pdf"
        was_cached = cache_fp.exists()
        try:
            pdf = fetch_ptr_pdf(doc_url)
        except Exception as exc:  # noqa: BLE001 — one bad fetch must not kill the run
            stats["fetch_errors"].append({"doc_id": doc_id, "error": str(exc)[:200]})
            print(f"  [fetch-error] {doc_id}: {exc}", flush=True)
            continue
        stats["pdfs_http" if not was_cached else "pdfs_cached"] += 1

        text = extract_ptr_text(pdf)
        if args.dump_text and i <= args.dump_text:
            DUMP_DIR.mkdir(parents=True, exist_ok=True)
            (DUMP_DIR / f"{doc_id}.txt").write_text(text, encoding="utf-8")
        if not text.strip():
            stats["no_text_pdfs"].append(doc_id)
            stats["filings_processed"] += 1
            continue

        result = parse_ptr_transactions(text)
        stats["filings_processed"] += 1
        stats["row_candidates"] += result.n_candidates
        stats["rows_parsed"] += len(result.rows)
        stats["rows_excluded"] += result.n_excluded

        filing_date = _norm_date(f.filing_date)
        for r in result.rows:
            tx_date = pd.Timestamp(r.date_transacted)
            rows.append({
                "member": str(f.member),
                "office": str(f.office),
                "filing_date": filing_date,
                "filing_year": int(f.filing_year),
                "doc_id": doc_id,
                "doc_url": doc_url,
                "owner": r.owner or "self",
                "asset": r.asset,
                "ticker": r.ticker,
                "asset_class": r.asset_class,
                "direction": r.direction,
                "raw_type": r.raw_type,
                "transaction_date": tx_date,
                "pdf_notification_date": pd.Timestamp(r.date_notified),
                "days_late": (
                    int((filing_date - tx_date).days)
                    if filing_date is not None else None
                ),
                "range_min": r.range_min,
                "range_max": r.range_max,
                "amount_range": r.amount_range,
            })
        if i % 25 == 0:
            print(
                f"  ...{i}/{len(filings)} filings, {len(rows)} rows, "
                f"{stats['row_candidates']} candidates",
                flush=True,
            )
    else:
        stats["complete"] = True

    stats["parse_failures"] = (
        stats["row_candidates"] - stats["rows_parsed"] - stats["rows_excluded"]
    )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(
            ["transaction_date", "filing_date", "member"], ascending=[False, False, True]
        ).reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    STATS.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    n_members = df["member"].nunique() if not df.empty else 0
    print(
        f"[ptr-tx-fetch] DONE{' (COMPLETE)' if stats['complete'] else ' (PARTIAL)'}: "
        f"{len(df)} transactions / {n_members} members; "
        f"processed {stats['filings_processed']}/{stats['filings_processed'] + len(stats['fetch_errors'])} "
        f"of {stats['filings_total']} filings; no-text {len(stats['no_text_pdfs'])}; "
        f"excluded(exchange) {stats['rows_excluded']}; "
        f"parse failures {stats['parse_failures']} "
        f"({stats['row_candidates']} candidates - {stats['rows_parsed']} parsed "
        f"- {stats['rows_excluded']} excluded) -> {OUT}",
        flush=True,
    )
    if stats["fetch_errors"]:
        print(f"[ptr-tx-fetch] fetch errors: {len(stats['fetch_errors'])}", flush=True)


if __name__ == "__main__":
    main()
