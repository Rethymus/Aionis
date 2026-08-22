"""Hermetic tests for 13F ingest pure functions (fixture-based, no network).

Fixtures are HAND-WRITTEN, labeled, and mimic real EDGAR structures (13F
information-table XML, SEC company_tickers snapshot entries) — no real data,
no network, per the project's mock-in-tests-only policy. Mirrors the testing
pattern of ``tests/test_form4.py``.

Covers the issuer-name → ticker EXACT-linking layer (``normalize_issuer_name``
+ ``build_issuer_ticker_map``) added to raise the /institutions panel's ticker
coverage: rendering-noise normalization (hit), legal-suffix/EDGAR-qualifier
normalization (hit), and the honest-miss paths (as-filed abbreviations,
ambiguous multi-entity names) that must stay null — never fuzzy-guessed.
"""
from __future__ import annotations

import pandas as pd

from aionis.ingest.form13f import (
    build_issuer_ticker_map,
    compute_changes,
    normalize_issuer_name,
    parse_infotable_xml,
)

# --- Fixture: minimal EDGAR-style 13F information table (hand-written) -------

_INFOTABLE_XML_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
    <infoTable>
        <nameOfIssuer>MOODYS CORP</nameOfIssuer>
        <titleOfClass>COM</titleOfClass>
        <cusip>615369105</cusip>
        <value>1000000</value>
        <shrsOrPrnAmt><sshPrnamt>2500</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
    </infoTable>
    <infoTable>
        <nameOfIssuer>NO SUCH ISSUER ABBREV</nameOfIssuer>
        <titleOfClass>COM</titleOfClass>
        <cusip>000000000</cusip>
        <value>10</value>
        <shrsOrPrnAmt><sshPrnamt>1</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
    </infoTable>
    <infoTable>
        <nameOfIssuer>SKIPPED EMPTY CUSIP</nameOfIssuer>
        <titleOfClass>COM</titleOfClass>
        <cusip></cusip>
        <value>10</value>
        <shrsOrPrnAmt><sshPrnamt>1</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
    </infoTable>
</informationTable>
"""

# --- Fixture: hand-written SEC company_tickers-snapshot-style triples --------
# (title, cik, ticker) in source order. Deliberately includes: the /DE/
# location qualifier, an apostrophe name, a multi-ticker single CIK (main
# listing first — Brookfield shape), a multi-CIK ambiguous name (iShares
# shape), a foreign N.V. legal form, and an empty title.
_SNAPSHOT_FIXTURE: list[tuple[str, int, str]] = [
    ("BANK OF AMERICA CORP /DE/", 70858, "BAC"),
    ("Moody's Corp /DE/", 1059556, "MCO"),
    ("BROOKFIELD Corp /ON/", 1001085, "BN"),  # main listing FIRST in source order
    ("BROOKFIELD Corp /ON/", 1001085, "BAMGF"),  # OTC preferred, same CIK
    ("BROOKFIELD Corp /ON/", 1001085, "BKPAF"),  # another OTC preferred
    ("iShares Inc.", 105470, "EWY"),
    ("iShares, Inc.", 1605888, "EWH"),  # DIFFERENT CIK, same normalized name
    ("Ferrovial N.V.", 1468522, "FER"),
    ("", 9999999, "XXXX"),  # empty title -> never linked
]


# --- normalize_issuer_name -----------------------------------------------------


def test_normalize_basic_and_leading_the() -> None:
    assert normalize_issuer_name("Apple Inc.") == "APPLE"
    assert normalize_issuer_name("THE COCA-COLA COMPANY") == "COCA COLA"
    assert normalize_issuer_name("Sea Ltd") == "SEA"


def test_normalize_legal_suffixes_and_del_marker() -> None:
    # INC·LTD·CORP-class suffixes and the EDGAR re-incorporation marker "DEL"
    # collapse identically on both naming conventions.
    assert normalize_issuer_name("BERKSHIRE HATHAWAY INC DEL") == "BERKSHIRE HATHAWAY"
    assert normalize_issuer_name("Berkshire Hathaway Inc") == "BERKSHIRE HATHAWAY"
    assert normalize_issuer_name("CROWDSTRIKE HLDGS INC") == "CROWDSTRIKE"
    assert normalize_issuer_name("Restaurant Brands International Inc") == "RESTAURANT BRANDS"


def test_normalize_apostrophes_edgar_qualifiers_and_foreign_forms() -> None:
    # "MOODY'S" (snapshot) vs "MOODYS" (as filed): the apostrophe is deleted,
    # not turned into a space — otherwise MOODY S != MOODYS.
    assert normalize_issuer_name("Moody's Corporation") == "MOODYS"
    assert normalize_issuer_name("MOODYS CORP") == "MOODYS"
    # EDGAR location qualifiers: mid, trailing-with-slash, trailing-bare.
    assert normalize_issuer_name("BANK OF AMERICA CORP /DE/") == "BANK OF AMERICA"
    assert normalize_issuer_name("VERISIGN INC/CA") == "VERISIGN"
    assert normalize_issuer_name("CANADIAN PACIFIC KANSAS CITY LTD/CN") == (
        "CANADIAN PACIFIC KANSAS CITY"
    )
    # Foreign legal forms fragment into single letters, which are dropped.
    assert normalize_issuer_name("Ferrovial N.V.") == "FERROVIAL"
    assert normalize_issuer_name("FERROVIAL NV") == "FERROVIAL"


def test_normalize_abbreviation_does_not_match_full_name() -> None:
    # As-filed abbreviations are NOT expanded — exact match only, no guessing.
    assert normalize_issuer_name("BANK OF AMER CORP") != normalize_issuer_name(
        "BANK OF AMERICA CORP /DE/"
    )
    assert normalize_issuer_name("APPLIED MATLS INC") != normalize_issuer_name(
        "Applied Materials, Inc."
    )
    assert normalize_issuer_name("") == ""
    assert normalize_issuer_name("///") == ""


# --- build_issuer_ticker_map ---------------------------------------------------


def test_build_map_exact_hit_and_qualifier_normalization() -> None:
    m = build_issuer_ticker_map(_SNAPSHOT_FIXTURE)
    assert m["BANK OF AMERICA"] == "BAC"
    assert m["MOODYS"] == "MCO"
    assert m["FERROVIAL"] == "FER"


def test_build_map_multi_ticker_single_entity_picks_first_plain_in_source_order() -> None:
    m = build_issuer_ticker_map(_SNAPSHOT_FIXTURE)
    # One CIK, three tickers: the FIRST plain (hyphen-free) ticker in source
    # order wins — the main listing BN, never an OTC preferred (BAMGF/BKPAF).
    assert m["BROOKFIELD"] == "BN"


def test_build_map_ambiguous_multi_entity_name_dropped() -> None:
    m = build_issuer_ticker_map(_SNAPSHOT_FIXTURE)
    # Two DIFFERENT CIKs normalize to "ISHARES" — ambiguous, so no link at all
    # (a picked ticker would be a guess about which fund the filer meant).
    assert "ISHARES" not in m


def test_build_map_skips_empty_titles() -> None:
    m = build_issuer_ticker_map(_SNAPSHOT_FIXTURE)
    assert "" not in m


def test_infotable_issuer_links_against_snapshot_fixture() -> None:
    # End-to-end shape: parse a (fixture) infotable, link its issuers through
    # the snapshot map — hit resolves, abbreviation misses stay None.
    m = build_issuer_ticker_map(_SNAPSHOT_FIXTURE)
    holdings = parse_infotable_xml(_INFOTABLE_XML_FIXTURE)
    assert [h.issuer for h in holdings] == ["MOODYS CORP", "NO SUCH ISSUER ABBREV"]
    linked = [m.get(normalize_issuer_name(h.issuer)) for h in holdings]
    assert linked == ["MCO", None]  # exact hit + honest miss, in filing order


# --- compute_changes (quarter-over-quarter frame diff, pure) ------------------

_COLS = ["cusip", "option_type", "issuer", "title_class", "value_usd", "shares"]


def _frame(rows: list[tuple[str, str, str, str, float, float]]) -> pd.DataFrame:
    """Hand-written EDGAR-aggregate-shaped frame (as export_form13f feeds it)."""
    return pd.DataFrame(rows, columns=_COLS)


def _by_cusip(rows: list[dict]) -> dict[str, dict]:
    return {r["cusip"]: r for r in rows}


def test_compute_changes_new_and_exited_carry_full_position_delta() -> None:
    prev = _frame([("111111111", "", "EXITED CORP", "COM", 2_000_000.0, 4_000.0)])
    cur = _frame([("222222222", "", "NEW CORP", "COM", 1_500_000.0, 1_000.0)])
    got = _by_cusip(compute_changes(prev, cur))
    new = got["222222222"]
    assert new["direction"] == "new" and new["delta_pct"] is None
    # new: delta_value = full position value added (whole USD)
    assert new["delta_value"] == 1_500_000.0
    exited = got["111111111"]
    assert exited["direction"] == "exited" and exited["delta_pct"] is None
    # exited: delta_value = full position value removed (negative)
    assert exited["delta_value"] == -2_000_000.0


def test_compute_changes_increased_reduced_delta_value_and_price_drift() -> None:
    # Same CUSIP both quarters: shares UP, value UP -> increased, both deltas positive.
    prev = _frame([("333333333", "", "HELD CORP", "COM", 1_000_000.0, 10_000.0)])
    cur = _frame([("333333333", "", "HELD CORP", "COM", 1_600_000.0, 12_500.0)])
    (row,) = compute_changes(prev, cur)
    assert row["direction"] == "increased"
    assert row["delta_pct"] == 25.0
    assert row["delta_value"] == 600_000.0

    # Shares DOWN but value UP (price drift): delta_pct negative while
    # delta_value positive — the sign MAY oppose; display layers must not
    # assume consistency (this is the case the web contract test
    # deliberately does not assert).
    cur_drift = _frame([("333333333", "", "HELD CORP", "COM", 1_200_000.0, 9_000.0)])
    (row2,) = compute_changes(prev, cur_drift)
    assert row2["direction"] == "reduced"
    assert row2["delta_pct"] == -10.0
    assert row2["delta_value"] == 200_000.0


def test_compute_changes_merges_tranches_before_diffing() -> None:
    # A filer splitting one issuer across two tranches in the current quarter:
    # the diff must see the SUMMED position (shares AND value), keyed on
    # (cusip, option_type) — not tranche rows.
    prev = _frame([("444444444", "", "SPLIT CORP", "COM", 500_000.0, 5_000.0)])
    cur = _frame(
        [
            ("444444444", "", "SPLIT CORP", "COM", 400_000.0, 4_000.0),
            ("444444444", "", "SPLIT CORP", "COM", 350_000.0, 3_500.0),
        ]
    )
    (row,) = compute_changes(prev, cur)
    assert row["direction"] == "increased"
    assert row["delta_pct"] == 50.0  # 8_500 vs 5_000 shares
    assert row["delta_value"] == 250_000.0  # 750_000 vs 500_000 value
