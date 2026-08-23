"""Bounded fetch of ApeWisdom's trending-stocks board (free public JSON API).

Thin runner over ``aionis.ingest.ape_wisdom``: every page of the
``filter/stocks`` ranking (≥2s spacing), plus an honest coverage probe of
the sibling filters. Output: ``data/cache/ape_wisdom_stocks.json``
(gitignored, regenerable) — a TODAY snapshot (ApeWisdom keeps no history;
repeat runs overwrite with the live board). Display lane ONLY.

Usage::

    uv run python scripts/ape_wisdom_fetch.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aionis.ingest.ape_wisdom import fetch_trending_stocks

OUT = Path("data/cache/ape_wisdom_stocks.json")


def main() -> None:
    data = fetch_trending_stocks()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": data["count"],
        "pages": data["pages"],
        "served_pages": data["served_pages"],
        "pagination_ok": data["pagination_ok"],
        "probe": data["probe"],
        "rows": data["rows"],
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    top = data["rows"][0] if data["rows"] else {}
    print(
        f"[ape-wisdom] {len(data['rows'])} tickers ({data['count']} declared, "
        f"{data['pages']} pages, served {data['served_pages']}, "
        f"pagination_ok={data['pagination_ok']}) -> {OUT}; top: "
        f"{top.get('ticker')} ({top.get('mentions')} mentions); "
        f"sibling filters: {data['probe']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
