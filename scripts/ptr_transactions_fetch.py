"""Bounded PTR transaction-level fetch (TASK-S, salvage revival — display-only).

Reads the COMMITTED filing-stream panel (``web/src/data/aionis/politician_trades.json``,
the House bulk FD.xml chain) and, for each filing's DocID PDF, decrypts +
extracts + parses transaction rows via :mod:`aionis.ingest.ptr_pdf` (revived
from the ``agent/politician`` salvage branch).

Honest coverage accounting (validated on a 20-PDF live sample, 2026-08-23):
- ``ok``      — mapped-font PDFs; rows parsed (12/20 in the sample, 45 rows).
- ``no_rows`` — text extracted but the row regex finds nothing: a mix of
  genuinely non-P/S documents and PARTIAL ToUnicode cmaps (2-byte CID fonts
  whose unmapped glyphs render as NUL — ``$200?``-style残迹; NOT recoverable
  via the stdlib cmap path). Counted, never guessed.
- ``no_text`` — no text layer (scanned paper PTR). Counted.

House Clerk PTR PDFs: U.S. Government public domain (17 U.S.C. §105). Polite
(>=2s host spacing, idempotent per-DocID cache under ``data/cache/``). Runs
are bounded by filing year (default 2026; ``--year 2025`` for the prior
batch). DISPLAY LANE ONLY.

Writes ``data/cache/ptr_transactions.parquet`` (gitignored, regenerable).

Usage::

    uv run python scripts/ptr_transactions_fetch.py            # 2026 batch
    uv run python scripts/ptr_transactions_fetch.py --year 2025
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

from aionis.ingest.ptr_pdf import extract_ptr_text, fetch_ptr_pdf, parse_ptr_rows

PANEL = Path("web/src/data/aionis/politician_trades.json")
OUT = Path("data/cache/ptr_transactions.parquet")

_DOC_URL_RE = re.compile(r"ptr-pdfs/(\d{4})/(\d+)\.pdf")


def main() -> None:
    year = int(sys.argv[sys.argv.index("--year") + 1]) if "--year" in sys.argv else 2026

    panel = json.loads(PANEL.read_text(encoding="utf-8"))
    filings = [p for p in panel["house"]["filings"] if p.get("filing_year") == year]
    if not filings:
        print(f"[ptr-tx] no {year} filings in the committed panel; nothing to do", flush=True)
        return
    print(f"[ptr-tx] {len(filings)} {year} PTR filings (filing-stream panel)", flush=True)

    running = pd.read_parquet(OUT) if OUT.exists() else None
    if running is not None and not running.empty:
        done_docs = set(running["doc_id"].astype(str))
        print(
            f"[ptr-tx] seeded aggregate: {len(running)} rows, {len(done_docs)} docs done",
            flush=True,
        )
    else:
        done_docs = set()

    rows: list[dict] = []
    counts = {"ok": 0, "no_rows": 0, "no_text": 0}
    for p in filings:
        m = _DOC_URL_RE.search(p.get("doc_url") or "")
        if not m:
            counts["no_text"] += 1
            continue
        doc_year, doc_id = int(m.group(1)), m.group(2)
        if doc_id in done_docs:
            # Parsed on a previous run — its rows live in the seed aggregate;
            # skip (idempotent re-run, counts below cover NEW docs only).
            continue
        try:
            pdf = fetch_ptr_pdf(doc_id, doc_year, cache_dir=Path("data/cache"))
            text = extract_ptr_text(pdf)
        except Exception as exc:  # bounded run: one bad doc never kills the batch
            print(f"[ptr-tx] FAIL {p['member'][:24]} doc={doc_id}: {exc}", flush=True)
            continue
        if len(text.strip()) < 50:
            counts["no_text"] += 1
            continue
        txs = parse_ptr_rows(text)
        if not txs:
            counts["no_rows"] += 1
            continue
        counts["ok"] += 1
        for t in txs:
            rows.append({
                "doc_id": doc_id,
                "member": p["member"],
                "office": p.get("office", ""),
                "party": p.get("party"),
                "filing_date": p.get("filing_date"),
                "owner": t.owner,
                "asset": t.asset,
                "ticker": t.ticker,
                "tx_type": t.tx_type,
                "raw_type": t.raw_type,
                "date_transacted": t.date_transacted.isoformat(),
                "date_disclosed": t.date_disclosed.isoformat(),
                "late_days": (t.date_disclosed - t.date_transacted).days,
                "range_min": t.range_min,
                "range_max": t.range_max,
                "doc_url": p["doc_url"],
            })
        print(
            f"[ptr-tx] OK {p['member'][:24]:24} doc={doc_id} rows={len(txs)}",
            flush=True,
        )

    if rows:
        fresh = pd.DataFrame(rows)
        running = fresh if running is None else pd.concat([running, fresh], ignore_index=True)
        running = running.drop_duplicates(
            subset=["doc_id", "owner", "asset", "tx_type", "date_transacted", "range_min"],
            keep="last",
        )
        OUT.parent.mkdir(parents=True, exist_ok=True)
        running.to_parquet(OUT, index=False)
    print(
        f"[ptr-tx] batch {year}: ok={counts['ok']} no_rows={counts['no_rows']} "
        f"no_text={counts['no_text']} | total rows "
        f"{0 if running is None else len(running)} -> {OUT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
