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

import pytest

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


def test_parse_volume_intensity_series_maps_to_volume() -> None:
    # timelinevol mode's series name is "Volume Intensity" — it must land in the
    # volume field (float-valued: it is an index, not a raw count).
    payload = {
        "timeline": [
            {"series": "Average Tone", "data": [{"date": "20170503", "value": 1.5}]},
            {"series": "Volume Intensity", "data": [{"date": "20170503", "value": 12.7}]},
        ]
    }
    rows = parse_timelinetone(payload)
    assert rows == [{"date": "20170503", "tone": 1.5, "volume": 12.7}]


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


def test_aggregate_groups_by_yyyymm_tone_mean_volume_mean() -> None:
    # volume is GDELT's Volume Intensity (0-100 attention index): monthly
    # aggregation is a MEAN (summing an index is meaningless). The old
    # sum-of-counts semantics rode on a series timelinetone never returned —
    # the panel's volume sat at a constant 0 for its whole history.
    rows = [
        {"date": "20170503", "tone": -3.0, "volume": 10.0},
        {"date": "20170510", "tone": -1.0, "volume": 30.0},
        {"date": "20170601", "tone": 2.0, "volume": 50.0},
    ]
    out = aggregate_monthly(rows)
    assert out == [
        {"month": "2017-05", "tone": -2.0, "volume": 20.0, "n": 2},
        {"month": "2017-06", "tone": 2.0, "volume": 50.0, "n": 1},
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


def test_merge_volume_none_inherits_cached_volume() -> None:
    # A tone-only refresh (its volume query 429'd) must NOT erase a previously
    # fetched attention reading — missing observation ≠ zero attention.
    cached = [{"month": "2026-08", "tone": 0.41, "volume": 37.5, "n": 28}]
    new = [{"month": "2026-08", "tone": 0.42, "volume": None, "n": 28}]
    merged = merge_series(cached, new)
    assert merged == [{"month": "2026-08", "tone": 0.42, "volume": 37.5, "n": 28}]


def test_aggregate_month_without_volume_observations_is_none() -> None:
    # Chunk whose volume query failed: tone rows carry no volume key → the
    # monthly row gets volume=None (the merge keeps the cached volume).
    rows = [{"date": "20260803", "tone": 0.5}, {"date": "20260804", "tone": -0.5}]
    out = aggregate_monthly(rows)
    assert out == [{"month": "2026-08", "tone": 0.0, "volume": None, "n": 2}]


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


# --- interior-gap backfill ---------------------------------------------------


def test_gap_backfill_windows_empty_without_gaps() -> None:
    months = [
        {"month": "2017-04"},
        {"month": "2017-05"},
        {"month": "2017-06"},
    ]
    assert nsg._gap_backfill_windows(months) == []
    assert nsg._gap_backfill_windows([]) == []
    assert nsg._gap_backfill_windows([{"month": "2017-04"}]) == []


def test_gap_backfill_windows_covers_single_missing_quarter() -> None:
    # 2025-06 → 2025-10 hole (observed in the committed panel): missing
    # 2025-07..2025-09 = one exact month-aligned run window (quarter alignment
    # would needlessly re-pull the cached 2025-06 and 2025-10).
    months = [{"month": m} for m in ("2025-06", "2025-10")]
    assert nsg._gap_backfill_windows(months) == [(date(2025, 7, 1), date(2025, 10, 1))]


def test_gap_backfill_windows_multiple_runs_one_window_per_run() -> None:
    # Contiguous 2018-04..2024-01 cache with exactly two holes: an isolated
    # 2018-05 and the observed five-month 2023-08..2023-12 run → two windows.
    def _range(lo: str, hi: str) -> list[str]:
        out = []
        cur = lo
        while cur < hi:
            out.append(cur)
            cur = nsg._month_add(cur)
        return out

    holes = {"2018-05", *"2023-08 2023-09 2023-10 2023-11 2023-12".split()}
    months = [{"month": m} for m in _range("2018-04", "2024-02") if m not in holes]
    assert nsg._gap_backfill_windows(months) == [
        (date(2018, 5, 1), date(2018, 6, 1)),
        (date(2023, 8, 1), date(2024, 1, 1)),
    ]


def test_collect_refetches_interior_gap_months(tmp_path: Path, monkeypatch) -> None:
    # A cache with 2025-06 + 2025-10 but nothing between: the collector must
    # issue a fetch window INSIDE history (the old forward-only cursor skipped
    # it forever), and the merged series must be contiguous after the stub
    # returns the missing months.
    cache_file = tmp_path / "gdelt_news_sentiment.json"
    cache_file.write_text(
        json.dumps(
            {
                "series": [
                    {"month": "2025-06", "tone": 0.15, "volume": 0, "n": 30},
                    {"month": "2025-10", "tone": 0.29, "volume": 0, "n": 28},
                ],
                "coverage_start": "2025-06",
                "coverage_end": "2025-10",
            }
        )
    )
    captured: list[tuple] = []

    def _fake_fetch(start, end, on_chunk=None):
        captured.append((start, end))
        return [
            {"month": "2025-07", "tone": 0.2, "volume": 3.0, "n": 31},
            {"month": "2025-08", "tone": 0.25, "volume": 4.0, "n": 31},
            {"month": "2025-09", "tone": 0.27, "volume": 5.0, "n": 30},
        ]

    monkeypatch.setattr(nsg, "fetch_tone_series", _fake_fetch)
    snap = collect_news_sentiment(
        start=DOC_API_EARLIEST, end=date(2025, 11, 1), cache_dir=tmp_path
    )
    # The tail from 2025-11 would be empty (end boundary), so the ONLY window
    # is the interior gap.
    assert captured == [(date(2025, 7, 1), date(2025, 10, 1))]
    assert [r["month"] for r in snap["series"]] == [
        "2025-06",
        "2025-07",
        "2025-08",
        "2025-09",
        "2025-10",
    ]


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
    def _fake_fetch(start, end, on_chunk=None):
        captured["start"] = start
        captured["end"] = end
        return [{"month": "2017-05", "tone": -1.0, "volume": 2, "n": 1}]
    monkeypatch.setattr(nsg, "fetch_tone_series", _fake_fetch)
    snap = collect_news_sentiment(
        start=DOC_API_EARLIEST, end=date(2017, 6, 1), cache_dir=tmp_path
    )
    assert captured["start"] == date(2017, 5, 1)  # delta only, not the cold start
    assert snap["n_months"] == 2  # cached April + fetched May


def test_collect_per_chunk_checkpoint_survives_timeout(tmp_path: Path, monkeypatch) -> None:
    # Root-cause #3 guard: if the cold backfill is killed mid-fetch (CI step
    # timeout — the 20-min cap), chunks already fetched must persist in the
    # cache. fetch_tone_series calls on_chunk after each chunk; collect's
    # callback writes the cache immediately. Simulate a kill after chunk 1 → the
    # cache must still hold chunk 1's month even though collect never finished.
    cache_path = tmp_path / "gdelt_news_sentiment.json"

    def _fake_fetch(start, end, on_chunk=None):
        # First chunk fetched + checkpointed via the callback…
        if on_chunk is not None:
            on_chunk([{"month": "2019-04", "tone": -3.0, "volume": 100, "n": 2}])
        # …then the CI step times out mid-backfill (process killed).
        raise RuntimeError("simulated CI step timeout")

    monkeypatch.setattr(nsg, "fetch_tone_series", _fake_fetch)
    with pytest.raises(RuntimeError):
        collect_news_sentiment(
            start=DOC_API_EARLIEST, end=date(2019, 12, 1), cache_dir=tmp_path
        )
    # The checkpoint wrote the cache BEFORE the timeout — partial data persists,
    # so a subsequent export reads real tone (not empty) and a later run resumes.
    assert cache_path.exists()
    on_disk = json.loads(cache_path.read_text())
    assert on_disk["n_months"] == 1
    assert on_disk["series"] == [
        {"month": "2019-04", "tone": -3.0, "volume": 100, "n": 2}
    ]


def test_collect_per_chunk_checkpoint_merges_across_chunks(tmp_path: Path, monkeypatch) -> None:
    # Normal multi-chunk backfill: on_chunk fires per chunk, cache accumulates.
    all_rows = [
        {"month": "2019-04", "tone": -3.0, "volume": 100, "n": 2},
        {"month": "2019-07", "tone": -1.0, "volume": 200, "n": 2},
    ]

    def _fake_fetch(start, end, on_chunk=None):
        # Real fetch_tone_series both invokes on_chunk AND returns the full list.
        for r in all_rows:
            if on_chunk is not None:
                on_chunk([r])
        return all_rows

    monkeypatch.setattr(nsg, "fetch_tone_series", _fake_fetch)
    snap = collect_news_sentiment(
        start=DOC_API_EARLIEST, end=date(2019, 12, 1), cache_dir=tmp_path
    )
    assert snap["n_months"] == 2
    cache_path = tmp_path / "gdelt_news_sentiment.json"
    assert cache_path.exists()
    on_disk = json.loads(cache_path.read_text())
    assert on_disk["n_months"] == 2
