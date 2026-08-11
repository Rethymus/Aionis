"""GDELT news-sentiment fetch for the ``news_sentiment`` theme (display-only).

Incremental fetch of GDELT Doc 2.0 ``timelinetone`` → monthly aggregate tone +
volume for US stock-market news (theme:ECON_STOCKMARKET). Writes ``data/cache/
gdelt_news_sentiment.json``, which ``export_themes`` consumes to populate the
``news_sentiment`` theme.

Cold start: backfills 2017-04 → today in quarterly chunks (one-time, ~36
queries × ≥15s ≈ 9 min). Subsequent runs: fetch only from the cached last
month + 1 (typically one chunk, ~15s) — daily-CI-cheap by design.

Display-only, exploratory. Does NOT enter the research pipeline (no lookahead
leakage). Polite: 15s host spacing (GDELT's documented minimum is ≥5s, but
sustained cold pulls at 5s triggered HTTP 429; 15s clears the throttle),
enforced by ``HostSpacingPolicy(min_interval=15.0)`` in the ingest module.

Usage::

    uv run python scripts/news_sentiment_gdelt_fetch.py

Re-run safely: incremental; existing cache is reused, only the delta is fetched.
"""
from __future__ import annotations

from aionis.ingest.news_sentiment_gdelt import DOC_API_EARLIEST, collect_news_sentiment


def main() -> None:
    snapshot = collect_news_sentiment()
    series = snapshot.get("series", [])
    print(
        f"[news-gdelt] coverage: {snapshot.get('coverage_start')} → "
        f"{snapshot.get('coverage_end')} ({snapshot.get('n_months', 0)} months)",
        flush=True,
    )
    if series:
        print(
            f"[news-gdelt] latest month {series[-1]['month']}: "
            f"tone={series[-1]['tone']}, volume={series[-1].get('volume', 0)}",
            flush=True,
        )
    else:
        print(
            f"[news-gdelt] WARNING: empty series (GDELT returned no tone rows "
            f"from {DOC_API_EARLIEST}); theme:ECON_STOCKMARKET may need revisiting",
            flush=True,
        )
    print("[news-gdelt] Complete.", flush=True)


if __name__ == "__main__":
    main()
