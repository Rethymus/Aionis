"""Bounded cover-price walk for the NEWEST priced (424B4) IPO filings.

Task-DISP-H3 second stage (the ``stakes_pct_parse.py`` precedent): select the
NEWEST ≤ ``--max-docs`` (default 80) ``status=priced`` rows from
``data/cache/form_ipo_aggregate.parquet``, fetch each filing's EDGAR
``index.json`` + primary 424B4 document (≤2 polite requests per row,
process-wide spacing raised to **2.1 s** + bounded transient-only retry) and
regex-extract the cover-page offer price into a graded confidence
(``exact`` / ``low`` / ``none`` — low never yields a value; see
``aionis.ingest.form_ipo_price``).

Request budget (owner brief 2026-08-26): ≤170 total requests for BOTH stages
— this walk defaults to ``--max-requests 156`` leaving ≥14 headroom for the
EFTS window refresh (``scripts/form_ipo_fetch.py``, ~13 pages); when the cap
is hit the walk stops wherever it is — cached rows survive, coverage stays
honest. Idempotent + resumable via ``data/cache/form_ipo_price_parsed.json``
(one entry per accession; ``ok`` entries are NEVER re-fetched ⇒ a rerun makes
ZERO new requests; failed entries retry on the next run).

Run AFTER ``scripts/form_ipo_fetch.py``, then re-run
``scripts/export_terminal_data.py``'s form_ipo exporter to merge prices into
the committed panel JSON.

Usage::

    uv run python scripts/form_ipo_price_parse.py              # newest 80 priced
    uv run python scripts/form_ipo_price_parse.py --max-docs 80 --max-requests 156
"""
from __future__ import annotations

import argparse
import time

import pandas as pd

from aionis.ingest import universe
from aionis.ingest.form_ipo_price import (
    CONF_EXACT,
    CONF_LOW,
    CONF_NONE,
    load_cache_meta,
    load_price_cache,
    parse_filing_offer_price,
    prune_price_cache_to_target,
    save_price_cache,
    stamp_row,
)
from aionis.ingest.http_policy import HostSpacingPolicy, HttpRequestPolicy

PARQUET = "data/cache/form_ipo_aggregate.parquet"
TASK_BUDGET = 170       # whole-task ceiling (EFTS window refresh + this walk)
DEFAULT_MAX_DOCS = 80   # target set cap: newest priced 424B4 filings


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-docs", type=int, default=DEFAULT_MAX_DOCS)
    ap.add_argument(
        "--max-requests", type=int, default=156,
        help="hard request cap for THIS walk (task budget %(default)s minus "
             "the EFTS window refresh headroom); 0 = VERIFY-ONLY dry pass "
             "(zero network — proves cached ok rows make no requests; ledger "
             "metadata is left untouched)",
    )
    args = ap.parse_args()

    df = pd.read_parquet(PARQUET)
    # Target set: status=priced (424B4) rows, newest filed_date first. The
    # aggregate is already newest-first; kind='stable' preserves its ordering
    # within a date so the same input always selects the same accessions.
    target = (
        df[df["status"] == "priced"]
        .sort_values("filed_date", ascending=False, kind="stable")
        .head(args.max_docs)
    )
    cache = load_price_cache()
    todo = [
        (int(r.issuer_cik), str(r.accession))
        for r in target.itertuples(index=False)
        if not cache.get(str(r.accession), {}).get("ok")
    ]
    cached_ok = sum(
        1 for acc in target["accession"] if cache.get(str(acc), {}).get("ok")
    )
    print(
        f"[ipo-price] priced={len(df[df['status'] == 'priced'])} "
        f"target(newest<={args.max_docs})={len(target)} "
        f"cached-ok={cached_ok} to-fetch={len(todo)}", flush=True,
    )

    if todo:
        # Owner directive for THIS lane: >=2.1 s host spacing (above the 2.0 s
        # project floor); keep the process-wide transient-only retry set.
        prev = universe._HTTP_POLICY
        universe._HTTP_POLICY = HttpRequestPolicy(
            spacing=HostSpacingPolicy(min_interval=2.1),
            retry_exceptions=prev._retry_exceptions,
        )

    n_req = 0
    stop_reason = ""
    t0 = time.monotonic()
    saved_meta = load_cache_meta()
    cumulative = int(saved_meta.get("requests_cumulative", 0))
    # A verify-only dry pass (--max-requests 0) touches NO network and must
    # NOT disturb the ledger metadata (walk_cap stays the last real walk's).
    live_walk = args.max_requests > 0

    def _run_meta() -> dict:
        if not live_walk:
            return saved_meta
        return {
            **saved_meta,
            "requests_cumulative": cumulative,
            "last_run": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "task_budget_requests": TASK_BUDGET,
            "walk_cap_requests": args.max_requests,
            "target_cap_docs": args.max_docs,
        }

    target_accessions = {str(a) for a in target["accession"]}

    def _save() -> None:
        # Cache hygiene on EVERY persist (cap early-exit, periodic and final
        # saves, and the --max-requests 0 dry pass): drop entries that slid
        # out of the target window. A slid-out accession can never re-enter
        # (filed dates are immutable), so this is zero information loss — and
        # it keeps the cache structurally equal to the disclosed window, so
        # the export layer's full-cache merge and its window-scoped exact
        # count can never drift apart again.
        save_price_cache(
            prune_price_cache_to_target(cache, target_accessions),
            meta=_run_meta(),
        )

    for i, (cik, acc) in enumerate(todo, 1):
        if n_req + 2 > args.max_requests:
            stop_reason = (
                f"REQUEST CAP {args.max_requests} reached after {i - 1}/{len(todo)}"
            )
            break
        res = parse_filing_offer_price(cik, acc)
        n_req += 2 if res["ok"] else 1
        cumulative += 2 if res["ok"] else 1
        cache[acc] = stamp_row({**res, "issuer_cik": cik})
        if i % 10 == 0 or i == len(todo):
            _save()
            print(
                f"[ipo-price] {i}/{len(todo)} ({(time.monotonic() - t0) / 60:.1f}min, "
                f"~{n_req} reqs this walk / {cumulative} cumulative) — {acc}: "
                f"{res['offer_price']} ({res['confidence']})"
                f"{'' if res['ok'] else ' ERROR ' + str(res['error'])}",
                flush=True,
            )
    _save()
    if stop_reason:
        print(f"[ipo-price] {stop_reason}", flush=True)

    # Honest coverage accounting over the TARGET set (not the cache).
    exact = low = none = fail = 0
    errors: dict[str, int] = {}
    for _, r in target.iterrows():
        e = cache.get(str(r["accession"])) or {}
        if e.get("ok") is False:
            fail += 1
            key = str(e.get("error") or "unknown").split(":")[0]
            errors[key] = errors.get(key, 0) + 1
            continue
        conf = e.get("confidence")
        if conf == CONF_EXACT:
            exact += 1
        elif conf == CONF_LOW:
            low += 1
        elif conf == CONF_NONE or e.get("offer_price") is None:
            none += 1
    print(
        f"[ipo-price] coverage over target {len(target)}: exact={exact} "
        f"(values exported) | low={low} (no value — never guessed) | "
        f"none={none} | fetch-failed={fail} {errors} | requests ~{n_req} "
        f"this walk, budget {args.max_requests} (task total <= {TASK_BUDGET})",
        flush=True,
    )


if __name__ == "__main__":
    main()
