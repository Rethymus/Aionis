"""Hermetic tests for the House PTR politician-trades ingest (no network).

The fixture mirrors the VERIFIED 2026-08-21 response shape of
``disclosures-clerk.house.gov/FinancialDisclosure/ViewMemberSearchResult``
(ASP.NET table rows: Name-with-PDF-link / Office / Filing Year / Filing) —
hand-written, labeled, per the project's mock-in-tests-only policy.
"""
from __future__ import annotations

from aionis.ingest.politician_trades import parse_house_ptr_html

# --- Fixture: hand-written mirror of the verified 2026 response shape --------

_HTML_FIXTURE = """
<table>
    <tbody>
        <tr role="row">
            <td data-label="Name" class="memberName">
                <a href="public_disc/ptr-pdfs/2026/20034201.pdf"
                   target="_blank">Alford, Hon.. Mark </a>
            </td>
            <td data-label="Office">MO04</td>
            <td data-label="Filing Year">2026</td>
            <td data-label="Filing">PTR Original</td>
        </tr>
        <tr role="row">
            <td data-label="Name" class="memberName">
                <a href="public_disc/ptr-pdfs/2026/20033945.pdf"
                   target="_blank">Morrison, Hon.. Kelly Louise </a>
            </td>
            <td data-label="Office">MN03</td>
            <td data-label="Filing Year">2026</td>
            <td data-label="Filing">PTR Amendment</td>
        </tr>
        <tr role="row">
            <td data-label="Name" class="memberName">
                <a href="public_disc/financial-pdfs/2026/10034945.pdf"
                   target="_blank">Someone, Hon.. Else </a>
            </td>
            <td data-label="Office">CA12</td>
            <td data-label="Filing Year">2026</td>
            <td data-label="Filing">Annual Report</td>
        </tr>
    </tbody>
</table>
"""


def test_parse_extracts_ptr_rows_with_absolute_pdf_urls() -> None:
    df = parse_house_ptr_html(_HTML_FIXTURE, filing_year=2026)
    assert len(df) == 2  # the Annual Report row is filtered out
    first = df.iloc[0]
    assert first["member"] == "Alford, Hon.. Mark"
    assert first["office"] == "MO04"
    assert first["filing_type"] == "PTR Original"
    assert first["filing_year"] == 2026
    assert first["doc_url"].startswith("https://disclosures-clerk.house.gov/")
    assert first["doc_url"].endswith("/ptr-pdfs/2026/20034201.pdf")


def test_parse_keeps_amendments_and_empty_input() -> None:
    df = parse_house_ptr_html(_HTML_FIXTURE, filing_year=2026)
    assert "PTR Amendment" in set(df["filing_type"])
    empty = parse_house_ptr_html("<html><body>no tables</body></html>", filing_year=2026)
    assert empty.empty
    assert list(empty.columns) == [
        "member", "office", "filing_type", "filing_year", "doc_url",
    ]


def test_parse_year_fallback_uses_argument() -> None:
    # If a row's Filing Year cell were empty, the caller-provided year anchors it.
    html = _HTML_FIXTURE.replace(
        '<td data-label="Filing Year">2026</td>',
        '<td data-label="Filing Year"></td>',
        1,
    )
    df = parse_house_ptr_html(html, filing_year=2025)
    assert int(df.iloc[0]["filing_year"]) == 2025
