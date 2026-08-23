"""Bounded document-parse of percent-of-class for the visible 13G/13D rows.

The second stage the /stakes-style state machine needs: for the rows the
panels actually SHOW (stakes_13g top-150 + smart_money top-120, read from the
committed web JSONs so the parsed set always matches the visible set), fetch
each filing's EDGAR index.json + primary document (≤2 polite requests per
row) and regex-extract ``pct_now`` / ``pct_prev`` (see
``aionis.ingest.stakes_pct``). Misses stay honest nulls; failures are counted
per cause, never retried to exhaustion within a run.

Idempotent + resumable: ``data/cache/stakes_pct_parsed.json`` keeps one entry
per accession; ``ok`` entries are never re-fetched, failed entries retry on
the next run. Hard time cap (default 45 min) stops the walk wherever it is —
already-cached rows survive, the export tolerates partial coverage by design
(null-tolerant rows).

Run AFTER ``export_terminal_data.py`` (it reads the exported panels), then
re-run the export to merge the pct fields into the rows.

Usage::

    uv run python scripts/stakes_pct_parse.py                # 13G 150 + 13D 120
    uv run python scripts/stakes_pct_parse.py --max-minutes 45
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from aionis.ingest.stakes_pct import (
    load_pct_cache,
    parse_filing_pct,
    save_pct_cache,
    stamp_row,
)

WEB = Path("web/src/data/aionis")


def _acc_from_url(url: str) -> str:
    """Accession (dashed) from an EDGAR archive URL; '' when absent."""
    if not url:
        return ""
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    tail = tail.removesuffix("-index.htm").removesuffix("-index.html")
    return tail if re.fullmatch(r"\d{10}-\d{2}-\d{6}", tail) else ""


def _cik_from_url(url: str) -> int | None:
    m = re.search(r"/data/(\d+)/", url or "")
    return int(m.group(1)) if m else None


def _visible_rows(panel: dict, *, rows_key: str, url_key: str) -> list[dict]:
    """[{accession, cik, form, is_amendment, url}] for the panel's visible rows.

    Rows without a resolvable EDGAR archive url (EFTS-era smart_money rows)
    keep an empty accession — counted as honest no-url failures, never parsed.
    """
    out = []
    for r in panel.get(rows_key) or []:
        url = str(r.get(url_key, ""))
        form = str(r.get("form", ""))
        out.append({
            "accession": _acc_from_url(url),
            "cik": _cik_from_url(url),
            "form": form,
            "is_amendment": form.endswith("/A"),
            "url": url,
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--max-minutes", type=float, default=45.0,
        help="hard wall-clock cap for this run (default 45; cache keeps progress)",
    )
    args = ap.parse_args()

    sg = json.loads((WEB / "stakes_13g.json").read_text(encoding="utf-8"))
    sm = json.loads((WEB / "smart_money.json").read_text(encoding="utf-8"))
    rows = (
        _visible_rows(sg, rows_key="filings", url_key="doc_url")
        + _visible_rows(sm, rows_key="recent_filings", url_key="url")
    )
    cache = load_pct_cache()
    todo = [
        r for r in rows
        if r["accession"] and not cache.get(r["accession"], {}).get("ok")
    ]
    n_rows = len(rows)
    n_no_url = sum(1 for r in rows if not r["accession"])
    print(
        f"[stakes-pct] visible rows: {n_rows} (13G {len(sg.get('filings') or [])} "
        f"+ 13D {len(sm.get('recent_filings') or [])}); {n_no_url} without url "
        f"(EFTS-era, honest null); {len(todo)} to fetch; "
        f"{len(rows) - n_no_url - len(todo)} cached-ok",
        flush=True,
    )

    deadline = time.monotonic() + args.max_minutes * 60
    n_req = 0
    t0 = time.monotonic()
    for i, r in enumerate(todo, 1):
        if time.monotonic() > deadline:
            print(
                f"[stakes-pct] TIME CAP {args.max_minutes:.0f}min hit at row "
                f"{i - 1}/{len(todo)} — cached rows survive, re-run to resume",
                flush=True,
            )
            break
        res = parse_filing_pct(
            r["cik"], r["accession"], is_amendment=r["is_amendment"]
        )
        n_req += 2 if res["ok"] else 1
        cache[r["accession"]] = stamp_row({**res, "form": r["form"]})
        if i % 10 == 0 or i == len(todo):
            save_pct_cache(cache)
            el = time.monotonic() - t0
            print(
                f"[stakes-pct] {i}/{len(todo)} ({el / 60:.1f}min elapsed, "
                f"{n_req} requests) — last {r['accession']} "
                f"now={res['pct_now']} prev={res['pct_prev']}"
                f"{'' if res['ok'] else ' ERROR ' + str(res['error'])}",
                flush=True,
            )
    save_pct_cache(cache)

    # Honest coverage accounting over the VISIBLE rows (not the cache).
    ok = fail = 0
    now_hit = prev_hit = 0
    errors: dict[str, int] = {}
    for r in rows:
        acc = r["accession"]
        if not acc:
            fail += 1
            errors["no_url"] = errors.get("no_url", 0) + 1
            continue
        e = cache.get(acc) or {}
        if e.get("ok"):
            ok += 1
            if e.get("pct_now") is not None:
                now_hit += 1
            if e.get("pct_prev") is not None:
                prev_hit += 1
        else:
            fail += 1
            key = str(e.get("error") or "not_parsed_yet").split(":")[0]
            errors[key] = errors.get(key, 0) + 1
    denom = max(ok, 1)
    print(
        f"[stakes-pct] coverage: ok {ok}/{len(rows)} rows | pct_now "
        f"{now_hit} ({now_hit / denom:.0%} of ok) | pct_prev {prev_hit} "
        f"| failures {fail} {errors}",
        flush=True,
    )


if __name__ == "__main__":
    main()
