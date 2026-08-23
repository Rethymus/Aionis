"""ApeWisdom trending-stocks API ingest — free, no-auth JSON (display-only).

ApeWisdom aggregates Reddit (r/wallstreetbets, r/stocks, …) ticker mentions;
its public JSON API needs no key (the same source xiaoyinsi's /reddit board
discloses). Verified live 2026-08-23 via browser: the domain is
**apewisdom.io** (the .com domain does not connect — the earlier 403s), and
only the ``filter/stocks`` view carries data — ``filter/all-posts`` and
``filter/crypto`` return an honest zero envelope on the same day, so the
INGEST pins the stocks filter and records the others' emptiness rather than
silently swapping endpoints.

Schema per result (first-party, stored verbatim — no derived fields):
``rank, ticker, name, mentions, upvotes, rank_24h_ago, mentions_24h_ago``;
envelope: ``count, pages, current_page, results``. Pagination follows the
envelope's own ``pages``/``current_page`` echo — on 2026-08-23 the free API
declared 3 pages/290 tickers but served page 1 only (100 rows) for every
pagination form, which the ingest records and discloses instead of padding.
≥2s spacing between page GETs via the process-wide ``HttpRequestPolicy`` +
explicit sleep.

Display lane ONLY — never a research signal, never PIT (a live board is a
today snapshot by definition; Aionis research uses frozen panels only).
"""
from __future__ import annotations

import time

import requests

from aionis.ingest.http_policy import HttpRequestPolicy, RetryPolicy

BASE = "https://apewisdom.io/api/v1.0"
# The stocks filter is the only endpoint verified to carry data; all-posts
# and crypto return {"count":0,...} envelopes (kept as a fact, not a swap).
STOCKS_URL = f"{BASE}/filter/stocks"

_POLICY = HttpRequestPolicy(retry_exceptions=(requests.RequestException,))
_UA = {"User-Agent": "Aionis-Research/1.0 (educational; contact via repo)"}


def _get(url: str, total_attempts: int = 3) -> requests.Response:
    retry = RetryPolicy(max_retries=total_attempts - 1, backoff_base=2.0)
    return _POLICY.request(
        url, lambda: requests.get(url, headers=_UA, timeout=30), retry=retry
    )


def fetch_trending_stocks(sleep_s: float = 2.1) -> dict:
    """Fetch the stocks filter politely, following the API's own pagination.

    2026-08-23 reality (browser-verified): the envelope DECLARES ``pages: 3,
    count: 290`` but every pagination form (``?page=N`` and path ``/N``)
    returns ``current_page: 1`` with the same first 100 rows — the free API
    serves page 1 only, at least today. The loop trusts the envelope's OWN
    ``current_page`` echo: a mismatch means pagination is dead, so it stops
    and records ``served_pages`` + ``pagination_ok`` for honest disclosure
    (the visible board is then the first 100 tickers of a declared 290 —
    disclosed, never padded or guessed).

    Returns ``{"rows": [...], "count": int, "pages": int,
    "served_pages": int, "pagination_ok": bool, "probe": {...}}``.
    """
    rows: list[dict] = []
    count = 0
    pages = 0
    page = 1
    served_pages = 0
    pagination_ok = True
    seen: set[tuple[int, str]] = set()
    while True:
        if page > 1:
            time.sleep(sleep_s)
        r = _get(STOCKS_URL + (f"?page={page}" if page > 1 else ""))
        r.raise_for_status()
        payload = r.json()
        if page == 1:
            count = int(payload.get("count") or 0)
            pages = int(payload.get("pages") or 1)
        # The envelope echoes the page it actually served — trust IT, not
        # our request, to decide whether pagination works at all.
        served = int(payload.get("current_page") or 1)
        if served != page:
            pagination_ok = False
            break
        served_pages = page
        batch = payload.get("results") or []
        for row in batch:
            key = (int(row.get("rank") or 0), str(row.get("ticker") or ""))
            if key not in seen:
                seen.add(key)
                rows.append(row)
        if page >= max(pages, 1) or not batch:
            break
        page += 1

    probe: dict[str, int] = {}
    siblings = (
        ("all_posts", f"{BASE}/filter/all-posts"),
        ("crypto", f"{BASE}/filter/crypto"),
    )
    for name, url in siblings:
        time.sleep(sleep_s)
        try:
            pr = _get(url)
            probe[name] = int((pr.json() or {}).get("count") or 0)
        except Exception:  # noqa: BLE001 — coverage probe is best-effort
            probe[name] = -1
    return {
        "rows": rows,
        "count": count,
        "pages": pages,
        "served_pages": served_pages,
        "pagination_ok": pagination_ok,
        "probe": probe,
    }
