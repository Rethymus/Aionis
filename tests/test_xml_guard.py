"""XXE / entity-expansion guard tests for aionis.ingest._xml_guard.

Pins (per the xxe-hardening task):

* the GUARD — ``fromstring_no_dtd`` refuses any DOCTYPE (the only syntactic
  place an ENTITY may appear) with ``XmlDtdForbiddenError``: the mini
  billion-laughs payload (5 layers x10) and an external-entity (SYSTEM)
  payload are both refused before any entity can expand;
* NON-REGRESSION — malformed XML still raises the stock ``ET.ParseError``
  the wired callers catch; the three wired entry points keep their existing
  error contracts (form4 / form13f degrade to ``[]`` + warning,
  politician_trades propagates);
* FIXTURE REUSE — the three modules' existing SEC/House XML fixtures parse
  to the same results the suites already pin (form13f: 2 issuers; form4: 2
  transactions; FD.xml: 3 PTR rows);
* HYGIENE — the sys.modules dance that obtains the pure parser leaves the
  C-accelerated ``xml.etree.ElementTree`` in place.

Premise note (pinned live in-session 2026-11-17, NOT re-run here because
deliberately feeding stock ET an entity payload is exactly what the repo's
security tooling flags): on this interpreter (expat 2.6.2) stock
``ET.fromstring`` expands the 5x10 nested entities to 100,000 chars with no
error, while external entities already fail with ``ParseError: undefined
entity`` — "outer blocked, inner blows up", which is why this guard refuses
the DOCTYPE outright.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET

import pytest
import test_form4
import test_form13f
import test_politician_trades

from aionis.ingest import form4, form13f, politician_trades
from aionis.ingest._xml_guard import XmlDtdForbiddenError, fromstring_no_dtd


def _mini_billion_laughs() -> str:
    """5 layers x10 internal entities -> 10^5 characters if expanded."""
    xml = '<!DOCTYPE r [<!ENTITY a0 "AAAAAAAAAA">'
    for i in range(1, 5):
        refs = (f"&a{i - 1};") * 10
        xml += f'<!ENTITY a{i} "{refs}">'
    xml += "]><r>&a4;</r>"
    return xml


# --- the guard ------------------------------------------------------------------


def test_guard_refuses_mini_billion_laughs() -> None:
    # Refused AT the DOCTYPE — before any entity can expand.
    with pytest.raises(XmlDtdForbiddenError):
        fromstring_no_dtd(_mini_billion_laughs())


def test_guard_refuses_external_entity_doctype() -> None:
    # A SYSTEM (external) entity payload is refused at the same DOCTYPE
    # gate, before resolution is ever attempted.
    with pytest.raises(XmlDtdForbiddenError):
        fromstring_no_dtd(
            '<!DOCTYPE r [<!ENTITY e SYSTEM "file:///etc/passwd">]><r>&e;</r>'
        )


def test_guard_keeps_stock_parse_error_behavior() -> None:
    with pytest.raises(ET.ParseError):
        fromstring_no_dtd("<r><a></r>")
    try:
        fromstring_no_dtd("not even xml")
    except ET.ParseError as exc:
        # exactly the C ET.ParseError class the wired callers catch
        assert type(exc) is ET.ParseError


# --- wired entry points keep their existing contracts ---------------------------


def test_wired_form4_and_form13f_refuse_dtd_gracefully() -> None:
    # These two degrade a bad document to [] + warning (their ParseError
    # contract) — the guard's refusal follows the same contract.
    doctyped = '<!DOCTYPE ownershipDocument [<!ENTITY a "x">]><ownershipDocument/>'
    assert form4.parse_form4_xml(doctyped) == []
    doctyped_13f = (
        '<!DOCTYPE informationTable [<!ENTITY a "x">]><informationTable/>'
    )
    assert form13f.parse_infotable_xml(doctyped_13f) == []


def test_wired_politician_trades_refuse_dtd_by_raising() -> None:
    # parse_fd_xml propagates parse errors today; the guard's refusal
    # propagates the same way (fail-closed, no silent [] here).
    doctyped_fd = (
        '<!DOCTYPE FinancialDisclosure [<!ENTITY a "x">]><FinancialDisclosure/>'
    )
    with pytest.raises(XmlDtdForbiddenError):
        politician_trades.parse_fd_xml(doctyped_fd, filing_year=2026)


# --- fixture reuse: real-shaped documents parse unchanged -----------------------


def test_existing_sec_fixtures_parse_unchanged_through_guard() -> None:
    # form13f — namespaced 13F informationTable (2 holdings pinned upstream).
    root = fromstring_no_dtd(test_form13f._INFOTABLE_XML_FIXTURE)
    assert root.tag.endswith("informationTable")
    holdings = form13f.parse_infotable_xml(test_form13f._INFOTABLE_XML_FIXTURE)
    assert [h.issuer for h in holdings] == ["MOODYS CORP", "NO SUCH ISSUER ABBREV"]

    # form4 — ownershipDocument (2 transactions pinned upstream).
    root4 = fromstring_no_dtd(test_form4._FORM4_XML_FIXTURE)
    assert root4.tag == "ownershipDocument"
    assert len(form4.parse_form4_xml(test_form4._FORM4_XML_FIXTURE)) == 2

    # politician_trades — House FD.xml bulk index (3 PTR rows pinned upstream).
    root_fd = fromstring_no_dtd(test_politician_trades._XML_FIXTURE)
    assert root_fd.tag == "FinancialDisclosure"
    df = politician_trades.parse_fd_xml(
        test_politician_trades._XML_FIXTURE, filing_year=2026
    )
    assert len(df) == 3


# --- hygiene: the pure-parser import dance restores the C accelerator -----------


def test_sys_modules_restored_after_guard_import() -> None:
    import _elementtree

    assert ET.XMLParser is _elementtree.XMLParser  # accelerator still in charge
    assert sys.modules["xml.etree.ElementTree"] is ET
    assert ET.fromstring("<x>1</x>").text == "1"
