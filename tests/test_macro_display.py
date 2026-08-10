"""Hermetic tests for the display-only macro fetcher (cache logic; no network).

The network path (``_fetch_observations``) is exercised by the manual run +
the daily cron; these tests cover the deterministic cache-hit short-circuit,
which is the load-bearing branch for ``--force`` vs cache-friendly invocations.
"""
from __future__ import annotations

import json
from pathlib import Path

from aionis.ingest.macro_display import DISPLAY_SERIES, fetch_display_series


def test_display_series_are_the_three_new_macro_additions() -> None:
    # The fetcher owns ONLY the display-only series; CPI/PAYEMS/DFF stay with
    # their research owners (macro_surprise / macro_dff).
    assert DISPLAY_SERIES == ("DTWEXBGS", "T10Y2Y", "UNRATE")


def test_cache_hit_returns_path_and_leaves_file_untouched(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    sid = "DTWEXBGS"
    cache_file = cache / f"alfred_{sid}.json"
    cache.mkdir(parents=True)
    payload = {
        "observations": [
            {"date": "2024-01-01", "realtime_start": "2024-01-02", "value": "115.0"},
            {"date": "2024-02-01", "realtime_start": "2024-02-02", "value": "."},
        ]
    }
    cache_file.write_text(json.dumps(payload))

    # Dummy key: a cache hit must short-circuit BEFORE any HTTP call, so the
    # key is never used — proving the no-network branch.
    out = fetch_display_series("DUMMY_KEY_NOT_USED", cache, sid, force=False)

    assert out == cache_file
    assert json.loads(cache_file.read_text()) == payload  # not rewritten/reformatted
