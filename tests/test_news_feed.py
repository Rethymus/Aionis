"""Hermetic tests for the GDELT news-feed ingest pure functions (no network).

Fixtures are HAND-WRITTEN, labeled, and mimic the REAL GDELT Doc 2.0 ``artlist``
JSON shape (field set observed on the 2026-08-22 probe: url / url_mobile /
title / seendate / socialimage / domain / language / sourcecountry) — no real
data, no network, per the project's mock-in-tests-only policy. Mirrors the
testing pattern of ``tests/test_form8k.py``.
"""
from __future__ import annotations

from datetime import date

from aionis.ingest.news_feed import (
    count_by_day,
    merge_feed,
    normalize_seendate,
    parse_artlist,
)

# HAND-WRITTEN FIXTURE (not real data) — artlist response shape as probed.
_FIXTURE = {
    "articles": [
        {
            "url": "https://example.com/us-stocks-rise",
            "url_mobile": "https://example.com/us-stocks-rise?amp",
            "title": "US stocks rise as bond market swings ease",
            "seendate": "20260821T180000Z",
            "socialimage": "https://cdn.example.com/img.jpeg",
            "domain": "example.com",
            "language": "English",
            "sourcecountry": "US",
        },
        {
            "url": "https://news.example.org/fed-holds-rates",
            "url_mobile": "",
            "title": "Federal Reserve holds rates steady",
            "seendate": "20260821T120000Z",
            "socialimage": "",
            "domain": "news.example.org",
            "language": "English",
            "sourcecountry": "",
        },
        # Missing title + empty sourcecountry → kept with honest empties.
        {
            "url": "https://wire.example.net/market-wrap",
            "url_mobile": "",
            "title": "",
            "seendate": "20260820T223000Z",
            "socialimage": "",
            "domain": "wire.example.net",
            "language": "",
            "sourcecountry": "",
        },
        # No url → cannot be deduped or linked → skipped + counted.
        {
            "url": "",
            "url_mobile": "",
            "title": "orphan entry with no url",
            "seendate": "20260820T120000Z",
            "socialimage": "",
            "domain": "orphan.com",
            "language": "English",
            "sourcecountry": "",
        },
    ]
}


# --- normalize_seendate -------------------------------------------------------


def test_normalize_valid_stamp() -> None:
    assert normalize_seendate("20260821T180000Z") == "2026-08-21T18:00:00Z"


def test_normalize_malformed_and_missing_become_empty() -> None:
    assert normalize_seendate("") == ""
    assert normalize_seendate(None) == ""
    assert normalize_seendate("not-a-stamp") == ""
    assert normalize_seendate("2026-08-21T18:00:00Z") == ""  # already ISO ≠ raw
    assert normalize_seendate("20260821T1800Z") == ""  # wrong length


# --- parse_artlist ------------------------------------------------------------


def test_parse_artlist_keeps_rows_and_honest_empties() -> None:
    rows = parse_artlist(_FIXTURE)
    assert len(rows) == 3  # the url-less orphan is skipped
    first = rows[0]
    assert first["url"] == "https://example.com/us-stocks-rise"
    assert first["title"] == "US stocks rise as bond market swings ease"
    assert first["seendate"] == "2026-08-21T18:00:00Z"
    assert first["domain"] == "example.com"
    assert first["language"] == "English"
    assert first["sourcecountry"] == "US"
    # Honest empties, never fabricated.
    third = rows[2]
    assert third["title"] == ""
    assert third["language"] == ""
    # url_mobile / socialimage are NOT carried (not part of the feed contract).


def test_parse_artlist_robust_to_malformed_payloads() -> None:
    assert parse_artlist({}) == []
    assert parse_artlist({"articles": []}) == []
    assert parse_artlist({"articles": [None, "junk", 42]}) == []
    assert parse_artlist({"timeline": []}) == []  # wrong mode → honest empty


# --- merge_feed ---------------------------------------------------------------


def test_merge_feed_dedupes_by_url_new_wins_and_sorts_desc() -> None:
    cached = [
        {"url": "a", "title": "old A", "seendate": "2026-08-01T00:00:00Z",
         "domain": "a.com", "language": "English", "sourcecountry": ""},
        {"url": "b", "title": "B", "seendate": "2026-08-15T00:00:00Z",
         "domain": "b.com", "language": "English", "sourcecountry": ""},
    ]
    new_rows = [
        {"url": "a", "title": "new A", "seendate": "2026-08-01T00:00:00Z",
         "domain": "a.com", "language": "English", "sourcecountry": ""},
        {"url": "c", "title": "C", "seendate": "2026-08-20T00:00:00Z",
         "domain": "c.com", "language": "English", "sourcecountry": ""},
    ]
    merged = merge_feed(cached, new_rows, keep_days=30, today=date(2026, 8, 22))
    urls = [r["url"] for r in merged]
    assert urls == ["c", "b", "a"]  # newest first, url-deduped
    by_url = {r["url"]: r for r in merged}
    assert by_url["a"]["title"] == "new A"  # new wins on content


def test_merge_feed_trims_window_on_seendate_date() -> None:
    rows = [
        {"url": "fresh", "seendate": "2026-08-22T10:00:00Z"},
        {"url": "edge", "seendate": "2026-07-23T23:00:00Z"},  # == cutoff day
        {"url": "stale", "seendate": "2026-07-01T00:00:00Z"},  # outside 30d
        {"url": "undated", "seendate": ""},  # cannot be placed → dropped
    ]
    merged = merge_feed([], rows, keep_days=30, today=date(2026, 8, 22))
    assert {r["url"] for r in merged} == {"fresh", "edge"}


# --- count_by_day -------------------------------------------------------------


def test_count_by_day_ascending_and_excludes_undated() -> None:
    rows = [
        {"seendate": "2026-08-21T18:00:00Z"},
        {"seendate": "2026-08-21T12:00:00Z"},
        {"seendate": "2026-08-22T00:00:00Z"},
        {"seendate": ""},
    ]
    assert count_by_day(rows) == [
        {"date": "2026-08-21", "count": 2},
        {"date": "2026-08-22", "count": 1},
    ]


def test_count_by_day_empty() -> None:
    assert count_by_day([]) == []
