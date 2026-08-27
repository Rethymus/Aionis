"""Bounded DEF 14A person-name DENOISE repair (TASK-DISP-D, display lane).

``scripts/export_terminal_data.py::export_def14a_persons`` reads
``data/cache/def14a_persons_parsed.json``, and pre-TASK-DISP-D parses glued
the roster age-column header onto captured names ("Charles M. Chiappone
Age") because the greedy age anchors absorbed the capitalized ``Age`` token.
:mod:`aionis.ingest.def14a_persons` strips that structural tail at capture
now; this thin runner brings the EXISTING parse cache back in line WITHOUT
re-walking the whole 150-filing panel:

1. scan the parse cache for filings whose stored persons still carry a bare
   trailing "Age" name suffix (the bug's exact fingerprint);
2. bounded refetch of ONLY those filings (<= ``MAX_DOCS`` primary documents,
   hard wall-clock budget) through the normal idempotent
   :func:`fetch_def14a_doc` path — >= 2.1s explicit spacing plus the
   process-wide host spacing, every HTTP GET recorded;
3. re-parse each doc with the FIXED parser and surgically replace ONLY that
   accession's record (persons / parsed / method / doc_url), preserving the
   original filing metadata and leaving all other records byte-untouched;
4. account honestly: ``n_requests`` accumulates the repair GETs on top of the
   last full fetch, and a ``repair_log`` block stores what ran, when, and
   how much it cost. Zero silent mutation — the report/printout carries the
   before -> after names per filing.

Offline fallback: cached index/doc files make this idempotent — a rerun
costs zero HTTP. If SEC is unreachable the script FAILS WITHOUT touching the
cache (no partial repair, no synthetic data — 宁可不动 不猜测).
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from aionis.ingest.def14a_persons import (
    fetch_def14a_doc,
    parse_def14a_persons,
)

CACHE = Path("data/cache/def14a_persons_parsed.json")
MAX_DOCS = 40  # hard bound well under the task budget (<= 40 documents)
BUDGET_SECONDS = 600.0


def _bare_age_suffix(name: str) -> bool:
    """True when a stored name still ends in the absorbed header token
    "Age" without its digits (the digits live in anchor group(2), so the
    parse cache shows exactly "... Age" fingerprints)."""
    return bool(re.search(r"\s+[Aa][Gg][Ee]$", name))


def main() -> None:
    payload = json.loads(CACHE.read_text(encoding="utf-8"))
    results: dict = payload.get("results", {})
    targets: dict[str, list[str]] = {}
    for acc, rec in results.items():
        dirty = [
            p["name"] for p in rec.get("persons") or [] if _bare_age_suffix(p["name"])
        ]
        if dirty:
            cik = str(rec.get("issuer_cik") or "").strip()
            if not cik:
                print(f"[repair] SKIP {acc}: dirty names but no issuer_cik", flush=True)
                continue
            targets[acc] = dirty
    if not targets:
        print("[repair] nothing to do: no bare-Age suffixed names in cache", flush=True)
        return
    if len(targets) > MAX_DOCS:
        raise SystemExit(
            f"[repair] {len(targets)} dirty filings exceeds MAX_DOCS={MAX_DOCS} "
            "(bounded lane violated) — aborting, cache untouched"
        )
    print(
        f"[repair] {len(targets)} filings carry bare-Age suffixed names: "
        + ", ".join(sorted(targets)),
        flush=True,
    )

    t0 = time.monotonic()
    requests: list[int] = []
    repairs: dict[str, dict] = {}
    for acc, dirty_before in sorted(targets.items()):
        rec = results[acc]
        cik = int(rec["issuer_cik"])
        if time.monotonic() - t0 > BUDGET_SECONDS:
            print(f"[repair] budget hit after {len(repairs)} repairs — stopping", flush=True)
            break
        text, doc_name = fetch_def14a_doc(cik, acc, request_counter=requests)
        if not text:
            print(
                f"[repair] {acc}: empty primary doc — LEAVING RECORD UNTOUCHED",
                flush=True,
            )
            continue
        n_before = len(rec.get("persons") or [])
        fresh = parse_def14a_persons(text)
        after_names = [p["name"] for p in fresh["persons"]]
        rec.update({
            "persons": fresh["persons"],
            "parsed": fresh["parsed"],
            "method": fresh["method"],
        })
        rec.pop("error", None)
        if doc_name:
            rec["doc_url"] = (
                f"https://www.sec.gov/Archives/edgar/data/{cik:010d}/"
                f"{acc.replace('-', '')}/{doc_name}"
            )
        repairs[acc] = {
            "company": rec.get("company", ""),
            "dirty_names_before": dirty_before,
            "persons_after": after_names,
            "n_persons_before_after": [n_before, len(after_names)],
        }
        print(
            f"[repair] {acc} ({rec.get('company', '')}): "
            f"{sum(1 for n in dirty_before)} dirty -> {len(after_names)} persons",
            flush=True,
        )

    if not repairs:
        print("[repair] nothing repaired (network or parse produced nothing) — "
              "cache left untouched", flush=True)
        return
    old_n = int(payload.get("n_requests", 0))
    payload["n_requests"] = old_n + len(requests)
    payload["repair_log"] = {
        "task": "TASK-DISP-D-def14a-name-denoise",
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "n_filings_repaired": len(repairs),
        "n_http_gets": len(requests),
        "n_http_gets_last_full_fetch": old_n,
        "details": repairs,
    }
    CACHE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8",
    )
    print(
        f"[repair] wrote cache: {len(repairs)} filings repaired, "
        f"{len(requests)} HTTP GETs (n_requests {old_n} -> {payload['n_requests']})",
        flush=True,
    )


if __name__ == "__main__":
    main()
