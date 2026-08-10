"""Hermetic tests for the GDELT news-sentiment ingest (no network).

The network path (``fetch_tone_series``) is exercised by the manual run + the
daily cron; these tests lock the load-bearing pure functions: the timelinetone
parser, the monthly aggregator, the cache-merge, the quarterly chunker, the
incremental-fetch cursor, and the top-level orchestrator with the network
monkeypatched out.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import aionis.ingest.news_sentiment_gdelt as nsg
from aionis.ingest.news_sentiment_gdelt import (
    DOC_API_EARLIEST,
    _chunk_quarters,
    _next_fetch_start,
    aggregate_monthly,
    collect_news_sentiment,
    merge_series,
    parse_timelinetone,
)

# --- parser ------------------------------------------------------------------


def test_parse_multi_series_collapses_to_one_row_per_date() -> None:
    payload = {
        "timeline": [
            {"series": "Average Tone", "data": [{"date": "20170503", "value": -3.5}]},
            {"series": "Article Volume", "data": [{"date": "20170503", "value": 1200}]},
        ]
    }
    rows = parse_timelinetone(payload)
    assert rows == [{"date": "20170503", "tone": -3.5, "volume": 1200}]


def test_parse_empty_payload_returns_empty() -> None:
    assert parse_timelinetone({}) == []
    assert parse_timelinetone({"timeline": []}) == []
    assert parse_timelinetone({"timeline": [{"series": "X", "data": []}]}) == []


def test_parse_skips_missing_values_and_dateless_points() -> None:
    payload = {
        "timeline": [
            {
                "series": "Average Tone",
                "data": [
                    {"date": "20170503", "value": -1.0},
                    {"date": "20170504"},  # missing value
                    {"value": 2.0},  # missing date
                ],
            },
        ]
    }
    rows = parse_timelinetone(payload)
    assert rows == [{"date": "20170503", "tone": -1.0}]


# --- monthly aggregator ------------------------------------------------------


def test_aggregate_groups_by_yyyymm_tone_mean_volume_sum() -> None:
    rows = [
        {"date": "20170503", "tone": -3.0, "volume": 100},
        {"date": "20170510", "tone": -1.0, "volume": 200},
        {"date": "20170601", "tone": 2.0, "volume": 50},
    ]
    out = aggregate_monthly(rows)
    assert out == [
        {"month": "2017-05", "tone": -2.0, "volume": 300, "n": 2},
        {"month": "2017-06", "tone": 2.0, "volume": 50, "n": 1},
    ]


def test_aggregate_empty_returns_empty() -> None:
    assert aggregate_monthly([]) == []


def test_aggregate_drops_months_with_no_tone() -> None:
    # A volume-only row (no tone) contributes nothing to sentiment → dropped.
    rows = [{"date": "20170503", "volume": 100}]
    assert aggregate_monthly(rows) == []


# --- merge -------------------------------------------------------------------


def test_merge_new_wins_on_duplicate_month() -> None:
    cached = [{"month": "2017-05", "tone": -9.9, "volume": 1, "n": 1}]
    new = [{"month": "2017-05", "tone": -2.0, "volume": 300, "n": 2}]
    merged = merge_series(cached, new)
    assert merged == [{"month": "2017-05", "tone": -2.0, "volume": 300, "n": 2}]


def test_merge_sorts_ascending_and_unions_disjoint_months() -> None:
    cached = [{"month": "2017-06", "tone": 1.0, "volume": 1, "n": 1}]
    new = [{"month": "2017-05", "tone": -2.0, "volume": 2, "n": 1}]
    merged = merge_series(cached, new)
    assert [m["month"] for m in merged] == ["2017-05", "2017-06"]


# --- quarterly chunker -------------------------------------------------------


def test_chunk_single_full_quarter() -> None:
    assert _chunk_quarters(date(2017, 4, 1), date(2017, 7, 1)) == [
        (date(2017, 4, 1), date(2017, 7, 1))
    ]


def test_chunk_three_quarters_in_one_year() -> None:
    chunks = _chunk_quarters(date(2017, 4, 1), date(2018, 1, 1))
    assert chunks == [
        (date(2017, 4, 1), date(2017, 7, 1)),
        (date(2017, 7, 1), date(2017, 10, 1)),
        (date(2017, 10, 1), date(2018, 1, 1)),
    ]


def test_chunk_aligns_to_calendar_quarter_boundary() -> None:
    # Mid-quarter start aligns back to the quarter's first month.
    chunks = _chunk_quarters(date(2017, 5, 15), date(2017, 7, 1))
    assert chunks == [(date(2017, 4, 1), date(2017, 7, 1))]


def test_chunk_empty_when_start_ge_end() -> None:
    assert _chunk_quarters(date(2017, 7, 1), date(2017, 4, 1)) == []
    assert _chunk_quarters(date(2017, 4, 1), date(2017, 4, 1)) == []


# --- incremental cursor ------------------------------------------------------


def test_next_fetch_start_cold_returns_clamped_cold_start() -> None:
    assert _next_fetch_start([], date(2017, 4, 1)) == date(2017, 4, 1)


def test_next_fetch_start_advances_one_month() -> None:
    assert _next_fetch_start([{"month": "2017-04"}], date(2017, 4, 1)) == date(2017, 5, 1)


def test_next_fetch_start_year_rollover() -> None:
    assert _next_fetch_start([{"month": "2017-12"}], date(2017, 4, 1)) == date(2018, 1, 1)


# --- orchestrator (network monkeypatched) ------------------------------------


def test_collect_writes_cache_and_archives_new_rows(tmp_path: Path, monkeypatch) -> None:
    # fetch_tone_series is the only network touchpoint; stub it to a known series.
    fake = [
        {"month": "2017-04", "tone": -3.0, "volume": 1000, "n": 3},
        {"month": "2017-05", "tone": -2.0, "volume": 1100, "n": 3},
    ]
    monkeypatch.setattr(nsg, "fetch_tone_series", lambda *a, **k: fake)
    snap = collect_news_sentiment(
        start=DOC_API_EARLIEST, end=date(2017, 6, 1), cache_dir=tmp_path
    )
    assert snap["n_months"] == 2
    assert snap["coverage_start"] == "2017-04"
    assert snap["coverage_end"] == "2017-05"
    assert snap["archive"]  # raw rows were sha256-archived
    cache_file = tmp_path / "gdelt_news_sentiment.json"
    assert cache_file.exists()
    on_disk = json.loads(cache_file.read_text())
    assert on_disk["series"] == fake


def test_collect_incremental_skips_when_cache_is_fresh(tmp_path: Path, monkeypatch) -> None:
    # Seed a cache already covering through the requested end.
    cache_file = tmp_path / "gdelt_news_sentiment.json"
    cache_file.write_text(
        json.dumps(
            {
                "series": [{"month": "2017-04", "tone": -3.0, "volume": 1, "n": 1}],
                "coverage_start": "2017-04",
                "coverage_end": "2017-04",
            }
        )
    )
    called = {"n": 0}
    monkeypatch.setattr(
        nsg,
        "fetch_tone_series",
        lambda *a, **k: called.__setitem__("n", called["n"] + 1) or [],
    )
    snap = collect_news_sentiment(
        start=DOC_API_EARLIEST, end=date(2017, 4, 30), cache_dir=tmp_path
    )
    assert called["n"] == 0  # cache fresh → no fetch
    assert snap["n_months"] == 1


def test_collect_incremental_fetches_only_delta(tmp_path: Path, monkeypatch) -> None:
    # Cache covers through 2017-04; fetch_start should be 2017-05.
    cache_file = tmp_path / "gdelt_news_sentiment.json"
    cache_file.write_text(
        json.dumps(
            {"series": [{"month": "2017-04", "tone": -3.0, "volume": 1, "n": 1}]}
        )
    )
    captured: dict = {}
    def _fake_fetch(start, end):
        captured["start"] = start
        captured["end"] = end
        return [{"month": "2017-05", "tone": -1.0, "volume": 2, "n": 1}]
    monkeypatch.setattr(nsg, "fetch_tone_series", _fake_fetch)
    snap = collect_news_sentiment(
        start=DOC_API_EARLIEST, end=date(2017, 6, 1), cache_dir=tmp_path
    )
    assert captured["start"] == date(2017, 5, 1)  # delta only, not the cold start
    assert snap["n_months"] == 2  # cached April + fetched May
