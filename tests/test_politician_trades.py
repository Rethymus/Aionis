"""Hermetic tests for the House PTR politician-trades ingest (no network).

The fixture mirrors the VERIFIED 2026-08-21 shape of the House Clerk bulk
``{year}FD.xml`` index (``Member`` entries with Prefix/Last/First/Suffix/
FilingType/StateDst/Year/FilingDate/DocID) — hand-written, labeled, per the
project's mock-in-tests-only policy. The bulk-ZIP path supersedes the
CSRF-token HTML search (same conclusion independently reached by the
concurrent session's diligence doc, agent/politician a2f719b).
"""
from __future__ import annotations

import pandas as pd

from aionis.ingest.politician_trades import _full_name, _norm_date, parse_fd_xml

# --- Fixture: hand-written mirror of the verified 2026 FD.xml shape ----------

_XML_FIXTURE = """<?xml version="1.0" encoding="utf-8"?>
<FinancialDisclosure>
  <Member>
    <Prefix>Hon.</Prefix>
    <Last>Alford</Last>
    <First>Mark</First>
    <Suffix />
    <FilingType>P</FilingType>
    <StateDst>MO04</StateDst>
    <Year>2026</Year>
    <FilingDate>8/5/2026</FilingDate>
    <DocID>20034201</DocID>
  </Member>
  <Member>
    <Prefix />
    <Last>Morrison</Last>
    <First>Kelly Louise</First>
    <Suffix />
    <FilingType>P</FilingType>
    <StateDst>MN03</StateDst>
    <Year>2026</Year>
    <FilingDate>6/11/2026</FilingDate>
    <DocID>20033945</DocID>
  </Member>
  <Member>
    <Prefix />
    <Last>Abdulle</Last>
    <First>Abdisallam</First>
    <Suffix />
    <FilingType>C</FilingType>
    <StateDst>MN02</StateDst>
    <Year>2026</Year>
    <FilingDate>6/11/2026</FilingDate>
    <DocID>10078673</DocID>
  </Member>
  <Member>
    <Prefix />
    <Last>NoDate</Last>
    <First>Someone</First>
    <Suffix />
    <FilingType>P</FilingType>
    <StateDst>TX31</StateDst>
    <Year>2025</Year>
    <FilingDate></FilingDate>
    <DocID>20040001</DocID>
  </Member>
  <Member>
    <Prefix />
    <Last>NoDocId</Last>
    <First>Ghost</First>
    <Suffix />
    <FilingType>P</FilingType>
    <StateDst>CA12</StateDst>
    <Year>2026</Year>
    <FilingDate>7/1/2026</FilingDate>
    <DocID></DocID>
  </Member>
</FinancialDisclosure>
"""


def test_parse_keeps_only_ptr_rows_with_dates_and_pdf_links() -> None:
    df = parse_fd_xml(_XML_FIXTURE, filing_year=2026)
    # C (candidate) row dropped; P row without DocID dropped.
    assert len(df) == 3
    first = df.iloc[0]
    assert first["member"] == "Alford, Hon. Mark"
    assert first["office"] == "MO04"
    assert first["filing_type"] == "PTR"
    assert first["filing_date"] == "2026-08-05"
    assert first["filing_year"] == 2026
    assert first["doc_url"] == (
        "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20034201.pdf"
    )


def test_parse_missing_date_is_null_and_empty_input() -> None:
    df = parse_fd_xml(_XML_FIXTURE, filing_year=2026)
    no_date = df[df["member"] == "NoDate, Someone"].iloc[0]
    # pandas renders the parser's None as NaN in an object column; the export
    # layer maps notna() -> value, NaN -> JSON null.
    assert pd.isna(no_date["filing_date"])
    empty = parse_fd_xml("<FinancialDisclosure></FinancialDisclosure>", filing_year=2026)
    assert empty.empty
    assert list(empty.columns) == [
        "member", "office", "filing_type", "filing_date", "filing_year", "doc_url",
    ]


def test_norm_date_formats() -> None:
    assert _norm_date("6/11/2026") == "2026-06-11"
    assert _norm_date("12/1/2025") == "2025-12-01"
    assert _norm_date("") is None
    assert _norm_date("2026-06-11") is None  # only M/D/YYYY as-filed form parses


def test_full_name_composition() -> None:
    assert _full_name("Hon.", "Alford", "Mark", "") == "Alford, Hon. Mark"
    assert _full_name("", "Morrison", "Kelly Louise", "") == "Morrison, Kelly Louise"
    assert _full_name("", "Smith", "Bob", "Jr.") == "Smith, Bob, Jr."
    assert _full_name("", "", "", "") == ""
