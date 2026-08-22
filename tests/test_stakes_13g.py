"""Hermetic tests for the daily-crawler-index SC 13G parser (no network).

Pins :mod:`aionis.ingest.stakes_13g`: the source is the EDGAR daily crawler
index (NOT EFTS — the EFTS ``search-index`` froze on the whole Schedule 13
family after 2024-12-17, live-verified 2026-08-22: ``forms=SC 13G`` returns 0
hits for every 2025+ window while the 2024 window tops out at 2024-12-17).
Rows are per-(accession, company): the index lists a filing under EVERY
covered company (subject AND filer), and the accession must strip EDGAR's
newer ``-index.htm`` suffix so it stays a stable join key. Subject/filer
resolution + ticker backfill live in the export lane (locked by the
``stakes_13g.json`` contract tests in ``tests/test_web_terminal_data.py``).

The network path (``fetch_daily_crawler_index``, reused from the 13D module
with a SHARED per-day cache) is exercised by the manual run + the daily cron.
"""
# ruff: noqa: E501  — the _SAMPLE_IDX fixture mirrors EDGAR's whitespace-aligned index format (inherently long lines).
from __future__ import annotations

from datetime import date

from aionis.ingest.stakes_13g import fetch_recent_13g_daily, parse_daily_13g

# A realistic-shaped EDGAR daily crawler index: ~6-line header, then whitespace-
# aligned data rows. SCHEDULE 13G rows mixed with unrelated forms (SC 13D,
# 13F-HR, 4) to prove the 13G-only filter; one accession listed under BOTH the
# subject and the filer entity (the live multi-name indexing), one /A
# amendment, a "-index.htm"-style URL (the newer live format), and one
# non-numeric-CIK junk row to prove the guard.
_SAMPLE_IDX = """Description:           Daily Crawler Index of EDGAR Dissemination Feed by Company Name
Last Data Received:    Aug 21, 2026
Comments:              webmaster@sec.gov




Company Name                                                  Form Type   CIK          Date       Filename
------------------------------------------------------------------------------------------
Catheter Precision, Inc.                                      SCHEDULE 13G     1716621     20260821    http://www.sec.gov/Archives/edgar/data/1716621/0000919574-26-005663-index.htm
C/M CAPITAL PARTNERS, LP                                      SCHEDULE 13G     2038499     20260821    http://www.sec.gov/Archives/edgar/data/2038499/0000919574-26-005663-index.htm
HARTE HANKS INC                                               SCHEDULE 13G/A   45919       20260821    http://www.sec.gov/Archives/edgar/data/45919/0002073679-26-000104-index.htm
ACRES Commercial Realty Corp.                                 SCHEDULE 13D     1332551     20260821    http://www.sec.gov/Archives/edgar/data/1332551/000090342026000123/
BLACKROCK INC                                                 13F-HR           1364742     20260821    http://www.sec.gov/Archives/edgar/data/1364742/000089093726001234/
JANE DOE (form 4, not a 13G)                                  4                 0           20260821    http://www.sec.gov/Archives/edgar/data/320193/000032019326000888/
WEIRD CO                                                      SCHEDULE 13G     NOTANUM     20260821    http://www.sec.gov/Archives/edgar/data/1/000000000026000001/
"""


def test_parse_extracts_only_schedule_13g_rows() -> None:
    rows = parse_daily_13g(_SAMPLE_IDX)
    # 3 SCHEDULE 13G rows (Catheter + C/M under the SAME accession + Harte /A);
    # the SC 13D, 13F-HR, Form 4, and junk-CIK rows must drop out.
    assert len(rows) == 3
    assert all(r["form"] in ("SC 13G", "SC 13G/A") for r in rows)
    names = {r["target"] for r in rows}
    assert names == {"Catheter Precision, Inc.", "C/M CAPITAL PARTNERS, LP",
                     "HARTE HANKS INC"}


def test_parse_same_accession_keeps_every_covered_company() -> None:
    """The index lists a filing under subject AND filer — the parser must keep
    both members (the export lane resolves which is which per accession)."""
    rows = parse_daily_13g(_SAMPLE_IDX)
    acc = [r for r in rows if r["accession"] == "0000919574-26-005663"]
    assert len(acc) == 2
    assert {r["target_cik"] for r in acc} == {1716621, 2038499}


def test_parse_strips_index_htm_suffix_from_accession() -> None:
    """Newer live rows end .../{accession}-index.htm — the accession must be the
    bare no-dash key so it joins across index formats (13D-era rows end /)."""
    rows = parse_daily_13g(_SAMPLE_IDX)
    for r in rows:
        assert not r["accession"].endswith("-index.htm")
        assert r["accession"] and " " not in r["accession"]


def test_parse_marks_amendments_and_forms() -> None:
    rows = parse_daily_13g(_SAMPLE_IDX)
    amendments = [r for r in rows if r["is_amendment"]]
    assert len(amendments) == 1
    assert amendments[0]["form"] == "SC 13G/A"
    assert amendments[0]["target"] == "HARTE HANKS INC"


def test_parse_fields_shape() -> None:
    rows = parse_daily_13g(_SAMPLE_IDX)
    cp = next(r for r in rows if r["target"] == "Catheter Precision, Inc.")
    assert cp["target_cik"] == 1716621
    assert cp["date"] == "2026-08-21"
    assert cp["url"].startswith("http://www.sec.gov/Archives/edgar/data/1716621/")


def test_parse_ignores_header_and_blank_lines() -> None:
    assert parse_daily_13g("Description: foo\n\nCompany Name  Form Type\n") == []


def test_parse_rejects_non_numeric_cik() -> None:
    assert parse_daily_13g(
        "WEIRD CO   SCHEDULE 13G   NOTANUM   20260821   https://x/y/z/"
    ) == []  # non-numeric CIK guard drops the malformed row


def test_fetch_recent_skips_weekends_returns_sorted(tmp_path) -> None:
    """The window walk covers business days only and returns newest-first rows
    (the fetch itself is the 13D module's shared, cron-exercised path)."""
    import aionis.ingest.stakes_13g as mod

    calls: list[date] = []

    def _fake_fetch(d, cache_dir=None, *, force=False):
        calls.append(d)
        return _SAMPLE_IDX if d.weekday() == 4 else ""  # only the Friday

    orig = mod.fetch_daily_crawler_index
    mod.fetch_daily_crawler_index = _fake_fetch
    try:
        rows = fetch_recent_13g_daily(date(2026, 8, 17), date(2026, 8, 21), tmp_path)
    finally:
        mod.fetch_daily_crawler_index = orig
    assert all(d.weekday() < 5 for d in calls)
    assert len(rows) == 3  # the Friday's 3 rows
    assert rows == sorted(rows, key=lambda r: r["date"], reverse=True)


def test_fetch_recent_survives_a_failed_day(tmp_path) -> None:
    """A 403/429 on one day must skip + continue, never kill the backfill."""
    import aionis.ingest.stakes_13g as mod

    def _fake_fetch(d, cache_dir=None, *, force=False):
        if d.weekday() == 1:
            raise RuntimeError("429 Too Many Requests")
        return _SAMPLE_IDX if d.weekday() == 4 else ""

    orig = mod.fetch_daily_crawler_index
    mod.fetch_daily_crawler_index = _fake_fetch
    try:
        rows = fetch_recent_13g_daily(date(2026, 8, 17), date(2026, 8, 21), tmp_path)
    finally:
        mod.fetch_daily_crawler_index = orig
    assert len(rows) == 3  # the Tuesday failure skipped; the Friday still parsed
