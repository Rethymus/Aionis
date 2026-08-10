#!/usr/bin/env python3
"""Fetch display-only ALFRED macro series for the terminal sub-panel.

Thin runner over :mod:`aionis.ingest.macro_display`. Fetches DTWEXBGS (trade-
weighted dollar), T10Y2Y (10Y−2Y Treasury spread), UNRATE (unemployment) into
``data/cache/alfred_{SID}.json``. These feed the macro-driver sub-panel's
dollar / yield-curve / mandate-tension cards via ``export_macro_drivers``.

Display-only: never enters the research pipeline. CPIAUCSL / PAYEMS / DFF are
owned by ``macro_surprise`` / ``macro_dff`` and are NOT touched here.

Run:
  uv run python scripts/fetch_macro_display.py            # cache-friendly
  uv run python scripts/fetch_macro_display.py --force    # re-fetch (cron)

Environment:
  FRED_API_KEY — required (read via aionis.config.settings).
"""
from __future__ import annotations

import sys

from aionis.config import settings
from aionis.ingest.macro_display import DISPLAY_SERIES, fetch_display_series


def main() -> int:
    if not settings.fred_api_key:
        print("ERROR: FRED_API_KEY required (set in .env)", file=sys.stderr)
        return 1
    force = "--force" in sys.argv[1:]
    cache = settings.data_dir / "cache"
    print(f"[fetch-macro-display] force={force} → {cache}/", flush=True)
    for sid in DISPLAY_SERIES:
        path = fetch_display_series(settings.fred_api_key, cache, sid, force=force)
        print(f"  {sid:>10}: {path.name}", flush=True)
    print("[fetch-macro-display] done.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
