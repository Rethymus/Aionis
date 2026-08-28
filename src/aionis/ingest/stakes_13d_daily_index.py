"""SC 13D filings via the EDGAR daily crawler index (display-only, exploratory).

The EFTS ``search-index`` stopped indexing SC 13D after 2024-12-17 (see memory
``aionis-edgar-efts-sc13d-frozen``). The EDGAR **daily crawler index**
(``crawler.{YYYYMMDD}.idx``) is the ground-truth, CURRENT dissemination feed —
one file per business day listing every filing disseminated, with company name,
form type, CIK, date, and URL. This module reads it to recover recent SC 13D
stakes that EFTS can no longer see.

EDGAR's daily crawler index is organized "by Company Name"; for SC 13D it lists
the filing under the **subject company** (the issuer/target whose securities are
reported — the reporting person is often an individual and is not indexed as a
"company"). So each parsed row gives the TARGET + its CIK + the filing date +
accession URL. The filer (activist) is in the cover page, not the index; left
blank here and surfaced honestly downstream.

Per-day checkpoint (resumable walk): each day-index file is date-keyed and
archived under ``daily-index/{year}/QTR{q}/crawler.{yyyymmdd}.idx`` — an
immutable snapshot once the day closes — so parsed rows cache permanently.
``fetch_recent_13d_daily`` persists them to the sidecar
``data/cache/sc13d_daily_checkpoint.json`` after EVERY day, so a killed walk
(timeout/CI cap) resumes with zero re-parsing and zero requests for cached
days. Each entry stores the sha256 of the raw day text and is reused only
while the locally cached raw index still hashes to it (disk-only check): the
one mutation window is the CURRENT day's file, which can still grow during
EDGAR's dissemination window (the cron captures it mid-window) — a changed
fingerprint recomputes just that day. The final aggregate is byte-identical
to the checkpoint-free walk.

Public domain (SEC). Polite via ``_policy_get`` (≥2s host spacing + backoff).
Filed-date PIT. Display-only, exploratory — NOT a research claim.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from aionis.config import settings
from aionis.ingest.universe import _policy_get

_UA = "Aionis research 13d-daily-index contact@example.com"
_DAILY_INDEX = "https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{q}/crawler.{yyyymmdd}.idx"
_CHECKPOINT_NAME = "sc13d_daily_checkpoint.json"
_CHECKPOINT_VERSION = 1
# Data rows are whitespace-aligned; fields are separated by 2+ spaces. The form
# type ("SCHEDULE 13D" / "SCHEDULE 13D/A") contains a single internal space, so a
# 2+-space split keeps it as one token.
_FIELD_SPLIT = re.compile(r"\s{2,}")


def _cache_dir(cache_dir: Path | None = None) -> Path:
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _daily_index_url(d: date) -> str:
    return _DAILY_INDEX.format(year=d.year, q=(d.month - 1) // 3 + 1, yyyymmdd=d.strftime("%Y%m%d"))


def _daily_index_cache_path(d: date, cache_dir: Path | None) -> Path:
    return _cache_dir(cache_dir) / f"daily_idx_{d.strftime('%Y%m%d')}.txt"


def _checkpoint_path(cache_dir: Path | None = None) -> Path:
    return _cache_dir(cache_dir) / _CHECKPOINT_NAME


def _fingerprint(text: str) -> str:
    """sha256 of a raw day-index text — the checkpoint's content link."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_checkpoint(cache_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load the per-day checkpoint sidecar.

    Shape: ``{iso_date: {"fingerprint": <sha256 of raw day text>, "rows": [...]}}``.
    Defensive by design — the sidecar is regenerable cache: a missing, corrupt,
    or unknown-version file yields ``{}`` and the walk recomputes every day from
    the raw day-index caches (zero extra requests) and rebuilds the sidecar.
    """
    fp = _checkpoint_path(cache_dir)
    if not fp.exists():
        return {}
    try:
        raw = json.loads(fp.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict) or raw.get("version") != _CHECKPOINT_VERSION:
        return {}
    days = raw.get("days")
    if not isinstance(days, dict):
        return {}
    return {
        d: e
        for d, e in days.items()
        if isinstance(e, dict)
        and isinstance(e.get("fingerprint"), str)
        and isinstance(e.get("rows"), list)
    }


def save_checkpoint(
    days: dict[str, dict[str, Any]], cache_dir: Path | None = None
) -> None:
    """Persist the checkpoint sidecar atomically (tmp write + replace).

    The checkpoint is ADVISORY: losing or skipping one save may cost re-parses
    on the next run, but it must NEVER kill the walk. Windows can deny the
    ``tmp.replace`` for seconds at a time (Defender/indexer holding the freshly
    written file — observed live as WinError 5, 2026-08-28), so the replace is
    retried with backoff and a direct write is the last-resort fallback; the
    defensive loader already tolerates a torn file.
    """
    import time

    fp = _checkpoint_path(cache_dir)
    fp.parent.mkdir(parents=True, exist_ok=True)
    tmp = fp.with_suffix(".json.tmp")
    payload = json.dumps({"version": _CHECKPOINT_VERSION, "days": days}, indent=2)
    for attempt in range(3):
        try:
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(fp)
            return
        except OSError:
            if attempt == 0:
                time.sleep(0.3)
            elif attempt == 1:
                time.sleep(1.0)
    # Last resort: direct write (non-atomic). If even that fails, drop the
    # save silently — the walk continues, the next day's save retries.
    try:
        fp.write_text(payload, encoding="utf-8")
    except OSError:
        pass


def fetch_daily_crawler_index(
    d: date, cache_dir: Path | None = None, *, force: bool = False
) -> str:
    """Fetch (and cache) one business day's crawler index text.

    Idempotent: a cached file is returned as-is unless ``force``. Weekends return
    an empty string (EDGAR disseminates nothing Sat/Sun).
    """
    if d.weekday() >= 5:
        return ""
    fp = _daily_index_cache_path(d, cache_dir)
    if fp.exists() and not force:
        return fp.read_text()
    url = _daily_index_url(d)
    r = _policy_get(
        url, total_attempts=4, backoff_base=4, headers={"User-Agent": _UA}, timeout=60
    )
    text = r.text
    fp.write_text(text)
    return text


def parse_daily_13d(idx_text: str) -> list[dict]:
    """Parse a crawler index text → SC 13D / SC 13D/A rows.

    Pure function (no network) — the load-bearing, hermetic-testable piece. Each
    row: {target, target_cik, date, form, is_amendment, accession, url}.

    The index header is ~6 descriptive lines; data rows follow. A data row's
    fields (Company Name | Form Type | CIK | Date | URL) are separated by 2+
    spaces. We keep only rows whose Form Type is ``SCHEDULE 13D`` or the ``/A``
    amendment.
    """
    out: list[dict] = []
    for line in idx_text.splitlines():
        fields = _FIELD_SPLIT.split(line.strip())
        # Need: company name, form, CIK, date, URL — 5 fields.
        if len(fields) < 5:
            continue
        form = fields[1]
        if form not in ("SCHEDULE 13D", "SCHEDULE 13D/A"):
            continue
        try:
            cik = int(fields[2])
        except ValueError:
            continue
        datestr = fields[3]
        if not re.fullmatch(r"\d{8}", datestr):
            continue
        url = fields[4]
        # accession = the directory name in the URL (.../{accession-no-dashes}/).
        accession = url.rstrip("/").rsplit("/", 1)[-1]
        out.append(
            {
                "target": fields[0].strip(),
                "target_cik": cik,
                "date": f"{datestr[:4]}-{datestr[4:6]}-{datestr[6:8]}",
                "form": "SC 13D/A" if form.endswith("/A") else "SC 13D",
                "is_amendment": form.endswith("/A"),
                "accession": accession,
                "url": url,
            }
        )
    return out


def fetch_recent_13d_daily(
    start: date,
    end: date,
    cache_dir: Path | None = None,
    *,
    force: bool = False,
    use_checkpoint: bool = True,
) -> list[dict]:
    """Every SC 13D filing in [start, end], business days only.

    Polite: one fetch per business day (the index lists ALL of that day's
    filings) — and only genuinely fetched/verified days touch the network;
    checkpoint hits make zero requests. Idempotent + resumable: each parsed
    day is persisted to the checkpoint sidecar immediately, so a killed walk
    resumes where it stopped — cached days are neither re-fetched nor
    re-parsed, only missing days are computed. Cached rows are reused while
    the locally cached raw day-index still hashes to the stored fingerprint
    (disk-only verification); a mismatch recomputes just that day.
    ``use_checkpoint=False`` restores the checkpoint-free path (identical
    output); ``force=True`` ignores the checkpoint and rebuilds it. Returns
    rows sorted newest-first — byte-identical to the checkpoint-free walk for
    the same input sequence.
    """
    rows: list[dict] = []
    checkpoint: dict[str, dict[str, Any]] = {}
    if use_checkpoint and not force:
        checkpoint = load_checkpoint(cache_dir)

    def _persist(d: date, text: str, day_rows: list[dict]) -> None:
        if not use_checkpoint:
            return
        checkpoint[str(d)] = {"fingerprint": _fingerprint(text), "rows": day_rows}
        save_checkpoint(checkpoint, cache_dir)

    cur = start
    while cur <= end:
        entry = checkpoint.get(str(cur))
        text = ""
        if entry is not None:
            # Checkpoint hit: re-verify the stored fingerprint against the
            # locally cached raw day-index (disk read + sha256 only — zero
            # requests, zero parsing), then reuse the persisted rows.
            raw_fp = _daily_index_cache_path(cur, cache_dir)
            if (
                raw_fp.exists()
                and _fingerprint(raw_fp.read_text()) == entry["fingerprint"]
            ):
                rows.extend(entry["rows"])
                cur += timedelta(days=1)
                continue
            # Raw index cache evicted: one polite re-fetch to re-verify the
            # fingerprint before trusting the persisted rows (no re-parse when
            # it still matches). A mismatch (same-day file grew, cache
            # rewritten) falls through and recomputes the day below.
            try:
                text = fetch_daily_crawler_index(cur, cache_dir)
            except Exception:
                cur += timedelta(days=1)
                continue
            if text and _fingerprint(text) == entry["fingerprint"]:
                rows.extend(entry["rows"])
                cur += timedelta(days=1)
                continue
        else:
            try:
                text = fetch_daily_crawler_index(cur, cache_dir, force=force)
            except Exception:
                # Per-day resilience: a 403/429/5xx on one day (EDGAR
                # rate-limits) must not kill the whole backfill. Skip +
                # continue; cached days still parse. A failed day gets NO
                # checkpoint entry, so the daily cron re-runs fill exactly the
                # missing days once EDGAR cools.
                cur += timedelta(days=1)
                continue
        if text:
            day_rows = parse_daily_13d(text)
            rows.extend(day_rows)
            _persist(cur, text, day_rows)
        cur += timedelta(days=1)
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows
