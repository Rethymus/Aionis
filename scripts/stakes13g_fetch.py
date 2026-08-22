"""Bounded daily fetch of recent SC 13G passive stakes via the EDGAR crawler index.

EFTS stopped indexing the Schedule 13 family after 2024-12-17 (verified live
2026-08-22: ``forms=SC 13G`` returns 0 hits for every 2025/2026 window — same
freeze as SC 13D, ``aionis-edgar-efts-sc13d-frozen``), so the 13G panel rides
the EDGAR daily crawler index, the same source that unfroze the 13D panel.
Default window: a trailing ~120 days (rolling anchor — the panel is a RECENT
passive-stake stream); one polite GET per business day (~85 requests cold,
≥2s spacing via ``_policy_get``), idempotent per-day caches (``daily_idx_*.txt``
shared with the 13D cron) so re-runs fetch only uncached days.

Writes ``data/cache/sc13g_daily_aggregate.json`` (gitignored, regenerable);
``scripts/export_terminal_data.py`` resolves subject/filer + ticker offline and
writes the tracked web payload (``stakes_13g.json``).

Usage::

    uv run python scripts/stakes13g_fetch.py              # trailing 120 days
    uv run python scripts/stakes13g_fetch.py --start 2026-06-01
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from aionis.ingest.stakes_13g import fetch_recent_13g_daily

OUT = Path("data/cache/sc13g_daily_aggregate.json")
# Trailing-window default: ~120 calendar days of passive-stake activity. END
# rolls with today; START rolls with it (a RECENT stream, unlike form8k's
# fixed anchor — 13G volume is ~30x 13D's, so the panel stays bounded).
_WINDOW_DAYS = 119


def _parse_start(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--start",
        type=_parse_start,
        default=date.today() - timedelta(days=_WINDOW_DAYS),
        help=f"window start (default: today - {_WINDOW_DAYS} days, a trailing ~120-day window)",
    )
    args = ap.parse_args()

    end = date.today()
    start = args.start
    span = (end - start).days
    print(f"[13g-daily] window {start} .. {end} ({span} calendar days)", flush=True)

    rows = fetch_recent_13g_daily(start, end)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2))
    n_acc = len({r["accession"] for r in rows})
    by_form: dict[str, int] = {}
    for r in rows:
        by_form[r["form"]] = by_form.get(r["form"], 0) + 1
    print(
        f"[13g-daily] wrote {len(rows)} index rows ({n_acc} distinct accessions, "
        f"{by_form}) to {OUT}",
        flush=True,
    )
    if rows:
        by_day: dict[str, int] = {}
        for r in rows:
            by_day[r["date"]] = by_day.get(r["date"], 0) + 1
        print(
            f"[13g-daily] days covered: {len(by_day)}  latest: {rows[0]['date']}  "
            f"{rows[0]['target'][:40]}",
            flush=True,
        )


if __name__ == "__main__":
    main()
