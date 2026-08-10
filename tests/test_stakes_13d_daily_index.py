"""Hermetic tests for the daily-crawler-index SC 13D parser (no network).

The network path (``fetch_daily_crawler_index``) is exercised by the manual run
+ the daily cron; these tests lock the load-bearing pure parser that turns the
EDGAR daily crawler index text into SC 13D rows.
"""
# ruff: noqa: E501  — the _SAMPLE_IDX fixture mirrors EDGAR's whitespace-aligned index format (inherently long lines).
from __future__ import annotations

from datetime import date

from aionis.ingest.stakes_13d_daily_index import fetch_recent_13d_daily, parse_daily_13d

# A realistic-shaped EDGAR daily crawler index: ~6-line header, then whitespace-
# aligned data rows. SC 13D rows mixed with unrelated forms (10-K, 4, 13F-HR) to
# prove the filter. One amendment (/A) + one row whose CIK is non-numeric (junk)
# to prove the guard.
_SAMPLE_IDX = """Description:           Daily Crawler Index of EDGAR Dissemination Feed by Company Name
Last Data Received:    Aug 7, 2026
Comments:              webmaster@sec.gov



Company Name                                                  Form Type   CIK          Date       Filename
------------------------------------------------------------------------------------------
ACRES Commercial Realty Corp.                                 SCHEDULE 13D     1332551     20260807    https://www.sec.gov/Archives/edgar/data/1332551/000090342026000123/
ACRES Commercial Realty Corp.                                 SCHEDULE 13D/A   1332551     20260807    https://www.sec.gov/Archives/edgar/data/1332551/000090342026000124/
APPLE INC                                                     10-K             320193      20260807    https://www.sec.gov/Archives/edgar/data/320193/000032019326000777/
2023 ETF Series Trust                                         SCHEDULE 13D/A   1969674     20260807    https://www.sec.gov/Archives/edgar/data/1969674/000089472026000045/
JANE DOE (insider form, not a 13D)                            4                 0           20260807    https://www.sec.gov/Archives/edgar/data/320193/000032019326000888/
BLACKROCK INC                                                 13F-HR           1364742     20260807    https://www.sec.gov/Archives/edgar/data/1364742/000089093726001234/
"""


def test_parse_extracts_only_schedule_13d_rows() -> None:
    rows = parse_daily_13d(_SAMPLE_IDX)
    # 3 SC 13D rows (2 ACRES + 1 ETF); the 10-K, Form 4, and 13F-HR must drop out.
    assert len(rows) == 3
    targets = {r["target"] for r in rows}
    assert targets == {"ACRES Commercial Realty Corp.", "2023 ETF Series Trust"}


def test_parse_marks_amendments_and_forms() -> None:
    rows = parse_daily_13d(_SAMPLE_IDX)
    amendments = [r for r in rows if r["is_amendment"]]
    originals = [r for r in rows if not r["is_amendment"]]
    # One original ACRES + one /A ACRES + one /A ETF → 2 amendments, 1 original.
    assert len(amendments) == 2
    assert len(originals) == 1
    assert all(r["form"] in ("SC 13D", "SC 13D/A") for r in rows)
    assert amendments[0]["form"] == "SC 13D/A"
    assert originals[0]["form"] == "SC 13D"


def test_parse_fields_shape() -> None:
    rows = parse_daily_13d(_SAMPLE_IDX)
    acres = next(r for r in rows if not r["is_amendment"])
    assert acres["target_cik"] == 1332551
    assert acres["date"] == "2026-08-07"
    assert acres["accession"] == "000090342026000123"
    assert acres["url"].startswith("https://www.sec.gov/Archives/edgar/data/1332551/")


def test_parse_ignores_header_and_blank_lines() -> None:
    # Header lines + blank lines + the column-headers row must not yield rows.
    rows = parse_daily_13d("Description: foo\n\nCompany Name  Form Type\n")
    assert rows == []


def test_parse_rejects_non_numeric_cik() -> None:
    rows = parse_daily_13d(
        "WEIRD CO   SCHEDULE 13D   NOTANUM   20260807   https://x/y/z/"
    )
    assert rows == []  # non-numeric CIK guard drops the malformed row


def test_fetch_recent_skips_weekends_returns_sorted(tmp_path) -> None:
    # fetch_recent_13d_daily loops calendar days but skips Sat/Sun (no fetch).
    # Monkeypatch the fetch to a known idx so no network is needed.
    import aionis.ingest.stakes_13d_daily_index as mod

    calls: list[date] = []

    def _fake_fetch(d, cache_dir=None, *, force=False):
        calls.append(d)
        # Return the sample only for the Friday; empty otherwise.
        return _SAMPLE_IDX if d.weekday() == 4 else ""

    orig = mod.fetch_daily_crawler_index
    mod.fetch_daily_crawler_index = _fake_fetch
    try:
        # A Mon→Fri window; only the Friday yields rows.
        rows = fetch_recent_13d_daily(date(2026, 8, 3), date(2026, 8, 7), tmp_path)
    finally:
        mod.fetch_daily_crawler_index = orig
    # No Sat/Sun in the window, but prove the loop walked business days.
    assert all(d.weekday() < 5 for d in calls)
    assert len(rows) == 3  # the Friday's 3 SC 13D rows
    assert rows == sorted(rows, key=lambda r: r["date"], reverse=True)
