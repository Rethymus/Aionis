"""Hermetic tests for the GDELT bilingual news-feed ingest (no network).

Fixtures are HAND-WRITTEN, labeled, and mimic the REAL GDELT Doc 2.0 ``artlist``
JSON shape (field set observed on the 2026-08-22 eng probe and the 2026-08-25
zho probe: url / url_mobile / title / seendate / socialimage / domain /
language / sourcecountry — language values observed as "English" / "Chinese")
— no real data, no network, per the project's mock-in-tests-only policy.
Mirrors the testing pattern of ``tests/test_form8k.py`` (pure parsers hermetic;
the network orchestrator monkeypatches ``fetch_articles``).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from aionis.ingest import news_feed as nf
from aionis.ingest.news_feed import (
    count_by_day,
    lang_code,
    load_cached_feed,
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

# HAND-WRITTEN FIXTURE (not real data) — zho-lane artlist shape (2026-08-25
# probe: wallstreetcn.com rows all carry language "Chinese").
_FIXTURE_ZHO = {
    "articles": [
        {
            "url": "https://wire.example.cn/earnings-flash",
            "title": "北方华创上半年营收同比增25%（手写样例，非真实数据）",
            "seendate": "20260825T100000Z",
            "domain": "wire.example.cn",
            "language": "Chinese",
            "sourcecountry": "China",
        },
        {
            "url": "https://wire.example.cn/macro-wrap",
            "title": "",
            "seendate": "20260825T040000Z",
            "domain": "wire.example.cn",
            "language": "",
            "sourcecountry": "China",
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


# --- lang_code (bilingual contract) -------------------------------------------


def test_lang_code_maps_api_language_names() -> None:
    assert lang_code("English") == "eng"
    assert lang_code("Chinese") == "zho"
    assert lang_code("  ENGLISH ") == "eng"  # case/whitespace tolerant


def test_lang_code_falls_back_to_provenance_then_empty() -> None:
    # API field absent/unmapped → per-request provenance labels the row.
    assert lang_code("", "eng") == "eng"
    assert lang_code("", "zho") == "zho"
    assert lang_code("Swahili", "zho") == "zho"  # unmappable API name → provenance
    # Neither source known → honest empty, never guessed from title bytes.
    assert lang_code("", "") == ""
    assert lang_code(None) == ""
    assert lang_code("English", "bogus") == "eng"  # valid API beats bogus provenance


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
    assert first["lang"] == "eng"  # derived from the API language field
    # Honest empties, never fabricated.
    third = rows[2]
    assert third["title"] == ""
    assert third["language"] == ""
    assert third["lang"] == ""  # no API field + no provenance → honest empty
    # url_mobile / socialimage are NOT carried (not part of the feed contract).


def test_parse_artlist_lang_api_field_wins_over_provenance() -> None:
    rows = parse_artlist(_FIXTURE_ZHO, provenance_lang="zho")
    assert rows[0]["language"] == "Chinese"
    assert rows[0]["lang"] == "zho"  # API-provided, not guessed
    # Empty API language on the zho-lane request → provenance fallback.
    assert rows[1]["language"] == ""
    assert rows[1]["lang"] == "zho"


def test_parse_artlist_robust_to_malformed_payloads() -> None:
    assert parse_artlist({}) == []
    assert parse_artlist({"articles": []}) == []
    assert parse_artlist({"articles": [None, "junk", 42]}) == []
    assert parse_artlist({"timeline": []}) == []  # wrong mode → honest empty


# --- merge_feed ---------------------------------------------------------------


def test_merge_feed_dedupes_by_url_new_wins_and_sorts_desc() -> None:
    cached = [
        {"url": "a", "title": "old A", "seendate": "2026-08-01T00:00:00Z",
         "domain": "a.com", "language": "English", "sourcecountry": "",
         "lang": "eng"},
        {"url": "b", "title": "B", "seendate": "2026-08-15T00:00:00Z",
         "domain": "b.com", "language": "English", "sourcecountry": "",
         "lang": "eng"},
    ]
    new_rows = [
        {"url": "a", "title": "new A", "seendate": "2026-08-01T00:00:00Z",
         "domain": "a.com", "language": "English", "sourcecountry": "",
         "lang": "eng"},
        {"url": "c", "title": "C", "seendate": "2026-08-20T00:00:00Z",
         "domain": "c.com", "language": "Chinese", "sourcecountry": "",
         "lang": "zho"},
    ]
    merged = merge_feed(cached, new_rows, keep_days=30, today=date(2026, 8, 22))
    urls = [r["url"] for r in merged]
    assert urls == ["c", "b", "a"]  # newest first, url-deduped
    by_url = {r["url"]: r for r in merged}
    assert by_url["a"]["title"] == "new A"  # new wins on content
    assert by_url["c"]["lang"] == "zho"  # lang rides through the merge


def test_merge_feed_trims_window_on_seendate_date() -> None:
    rows = [
        {"url": "fresh", "seendate": "2026-08-22T10:00:00Z", "lang": "eng"},
        {"url": "edge", "seendate": "2026-07-23T23:00:00Z", "lang": "zho"},  # == cutoff day
        {"url": "stale", "seendate": "2026-07-01T00:00:00Z", "lang": "eng"},  # outside 30d
        {"url": "undated", "seendate": "", "lang": "zho"},  # cannot be placed → dropped
    ]
    merged = merge_feed([], rows, keep_days=30, today=date(2026, 8, 22))
    assert {r["url"] for r in merged} == {"fresh", "edge"}


def test_merge_feed_cross_language_dedup_not_attempted() -> None:
    # Different articles in different languages coexist (task contract: no
    # cross-language dedup); only an EXACT url collision collapses.
    rows = [
        {"url": "https://en.example.com/a", "seendate": "2026-08-20T00:00:00Z",
         "lang": "eng"},
        {"url": "https://cn.example.com/a", "seendate": "2026-08-19T00:00:00Z",
         "lang": "zho"},
        {"url": "https://en.example.com/a", "seendate": "2026-08-18T00:00:00Z",
         "lang": "eng"},  # same url → deduped (one row)
    ]
    merged = merge_feed([], rows, keep_days=30, today=date(2026, 8, 22))
    assert len(merged) == 2
    assert {r["lang"] for r in merged} == {"eng", "zho"}


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


# --- load_cached_feed (legacy cache upgrade) -----------------------------------


def test_load_cached_feed_backfills_lang_on_legacy_cache(tmp_path: Path) -> None:
    # Pre-bilingual cache (no lang column): every row came exclusively from
    # the eng-only DEFAULT_QUERY era → provenance backfill "eng", not a guess.
    legacy = pd.DataFrame(
        [
            {
                "url": "https://legacy.example.com/a",
                "title": "Legacy row",
                "seendate": "2026-08-20T00:00:00Z",
                "domain": "legacy.example.com",
                "language": "English",
                "sourcecountry": "US",
            }
        ]
    )
    legacy.to_parquet(tmp_path / "news_feed.parquet", index=False)
    rows = load_cached_feed(tmp_path)
    assert len(rows) == 1
    assert rows[0]["lang"] == "eng"


def test_load_cached_feed_keeps_existing_lang(tmp_path: Path) -> None:
    modern = pd.DataFrame(
        [
            {"url": "https://a.example.com/x", "title": "A",
             "seendate": "2026-08-20T00:00:00Z", "domain": "a.example.com",
             "language": "Chinese", "sourcecountry": "China", "lang": "zho"},
        ]
    )
    modern.to_parquet(tmp_path / "news_feed.parquet", index=False)
    rows = load_cached_feed(tmp_path)
    assert rows[0]["lang"] == "zho"  # existing codes pass through untouched


# --- collect_news_feed orchestrator (network monkeypatched) ---------------------


def _fake_rows(urls: list[str], *, lang: str, language: str, day: str) -> list[dict]:
    return [
        {
            "url": u,
            "title": f"row {u} ({lang})",
            "seendate": f"{day}T12:00:00Z",
            "domain": f"{lang}.example.com",
            "language": language,
            "sourcecountry": "",
            "lang": lang,
        }
        for u in urls
    ]


def test_collect_fetches_both_lanes_and_writes_lang(tmp_path, monkeypatch) -> None:
    # fetch_articles is the only network touchpoint; stub per-lane results and
    # capture which (query, lang) lanes actually fired.
    calls: list[tuple[str, str]] = []

    def _fake_fetch(*, query: str, timespan: str, lang: str = "") -> list[dict]:
        calls.append((query, lang))
        if lang == "zho":
            return _fake_rows(
                ["https://cn.example.com/z1", "https://cn.example.com/z2"],
                lang="zho", language="Chinese", day="2026-08-25",
            )
        return _fake_rows(
            ["https://en.example.com/e1"], lang="eng", language="English",
            day="2026-08-24",
        )

    monkeypatch.setattr(nf, "fetch_articles", _fake_fetch)
    merged = nf.collect_news_feed(cache_dir=tmp_path)

    # BOTH polite lanes fired exactly once each, with the lane provenance.
    assert sorted(c[1] for c in calls) == ["eng", "zho"]
    assert any("wallstreetcn.com" in c[0] for c in calls if c[1] == "zho")

    # Contract: lang on every item, lang ∈ {eng, zho}, zho > 0.
    assert all(r.get("lang") in ("eng", "zho") for r in merged)
    langs = [r["lang"] for r in merged]
    assert langs.count("zho") == 2
    assert langs.count("eng") == 1

    # Parquet written with the lang column, readable back identically.
    df = pd.read_parquet(tmp_path / "news_feed.parquet")
    assert "lang" in df.columns
    assert set(df["lang"]) == {"eng", "zho"}


def test_collect_single_lane_failure_degrades_honestly(
    tmp_path, monkeypatch
) -> None:
    # Seed a cache with one old zho row, then let the zho lane fail while the
    # eng lane succeeds: the eng merge proceeds, the old zho row survives the
    # 30-day window, and no exception escapes.
    pd.DataFrame(
        [
            {"url": "https://cn.example.com/old", "title": "old zho",
             "seendate": "2026-08-20T00:00:00Z", "domain": "cn.example.com",
             "language": "Chinese", "sourcecountry": "China", "lang": "zho"},
        ]
    ).to_parquet(tmp_path / "news_feed.parquet", index=False)

    def _fake_fetch(*, query: str, timespan: str, lang: str = "") -> list[dict]:
        if lang == "zho":
            raise nf.HTTPStatusError(429, 3)
        return _fake_rows(
            ["https://en.example.com/e1"], lang="eng", language="English",
            day="2026-08-25",
        )

    monkeypatch.setattr(nf, "fetch_articles", _fake_fetch)
    merged = nf.collect_news_feed(cache_dir=tmp_path)
    urls = {r["url"] for r in merged}
    assert "https://en.example.com/e1" in urls  # surviving lane merged
    assert "https://cn.example.com/old" in urls  # failed lane's cache retained


def test_collect_total_failure_keeps_old_cache_and_raises(
    tmp_path, monkeypatch
) -> None:
    old = pd.DataFrame(
        [
            {"url": "https://en.example.com/old", "title": "old eng",
             "seendate": "2026-08-20T00:00:00Z", "domain": "en.example.com",
             "language": "English", "sourcecountry": "US", "lang": "eng"},
        ]
    )
    old.to_parquet(tmp_path / "news_feed.parquet", index=False)

    def _always_fail(**kwargs):
        raise nf.HTTPStatusError(429, 3)

    monkeypatch.setattr(nf, "fetch_articles", _always_fail)
    with pytest.raises(nf.HTTPStatusError):
        nf.collect_news_feed(cache_dir=tmp_path)
    # Old cache untouched (mtime-invariant content check).
    assert pd.read_parquet(tmp_path / "news_feed.parquet")["url"].tolist() == [
        "https://en.example.com/old"
    ]


# --- REAL-cache contract (skipped when the fetch has not run here) --------------

_REAL_CACHE = Path("data/cache/news_feed.parquet")


def test_real_cache_lang_contract_if_fetched() -> None:
    """Runs only where the REAL bilingual fetch has populated the cache.

    Pins the live contract: ``lang`` on every cached row, lang ∈ {eng, zho},
    and a non-empty Chinese stream (zho > 0) — the panel's honest bilingual
    depth claim. Skips in hermetic/CI environments without data/cache (the
    fetcher runs there separately; the panel keeps its committed JSON).
    """
    if not _REAL_CACHE.exists():
        pytest.skip("real news_feed cache not present (fetch not run here)")
    rows = load_cached_feed()
    assert rows, "cache present but empty"
    assert all(r.get("lang") in ("eng", "zho") for r in rows), (
        "lang must exist on every item and be one of the two lane codes"
    )
    assert sum(1 for r in rows if r["lang"] == "zho") > 0, (
        "the real bilingual fetch must have contributed Chinese rows"
    )
