"""Fetch the Korea risk-appetite proxy (FRED DEXKOUS) — display-only.

Thin runner over ``aionis.ingest.korea_proxy``: one polite FRED request
(weekly series, 2015+ ≈ 600 rows, single page). Output:
``data/cache/korea_proxy_usdkrw.json`` (gitignored, idempotent).

Usage::

    uv run python scripts/korea_proxy_fetch.py [--force]
"""
from __future__ import annotations

import re
import sys

from aionis.ingest.korea_proxy import SERIES_ID, SERIES_TITLE, fetch_korea_proxy


def _fred_key() -> str:
    for line in open(".env", encoding="utf-8", errors="ignore"):
        m = re.match(r"FRED_API_KEY\s*=\s*(\S+)", line)
        if m:
            return m.group(1)
    raise SystemExit("FRED_API_KEY not found in .env")


def main() -> None:
    force = "--force" in sys.argv
    fp = fetch_korea_proxy(_fred_key(), force=force)
    import json

    data = json.loads(fp.read_text())
    obs = data["observations"]
    print(
        f"[korea-proxy] {SERIES_ID} ({SERIES_TITLE}): {len(obs)} weekly rows, "
        f"{obs[0]['date']} .. {obs[-1]['date']}, latest {obs[-1]['value']} -> {fp}",
        flush=True,
    )


if __name__ == "__main__":
    main()
