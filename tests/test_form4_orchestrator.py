"""Hermetic tests for the Form 4 XML-fetch orchestrator (no network).

Monkeypatches ``_policy_get`` and ``fetch_form4_filings`` so nothing touches the
network. Reuses the Form 4 XML shape from ``tests/test_form4.py``.
"""
from __future__ import annotations

import pandas as pd

from aionis.ingest import form4_orchestrator as orch


class _FakeResp:
    def __init__(self, *, json_data: dict | None = None, text: str = "") -> None:
        self._json = json_data
        self.text = text

    def json(self) -> dict:
        return self._json or {}


_INDEX_XML_DOC = {"directory": {"item": [
    {"name": "form4_index.htm"},
    {"name": "primary_doc.xml"},
]}}

_INDEX_TXT_ONLY = {"directory": {"item": [
    {"name": "form4_index.htm"},
    {"name": "000123456725000001.txt"},
]}}

_FORM4_XML = """<?xml version="1.0"?>
<ownershipDocument>
  <documentType>4</documentType>
  <issuer><issuerCik>0000320193</issuerCik><issuerTradingSymbol>AAPL</issuerTradingSymbol></issuer>
  <reportingOwner><reportingOwnerId><rptOwnerCik>0001234567</rptOwnerCik><rptOwnerName>JOHN DOE</rptOwnerName></reportingOwnerId></reportingOwner>
  <nonDerivativeTable><nonDerivativeTransaction>
    <transactionDate><year>2024</year><month>1</month><day>15</day></transactionDate>
    <transactionCoding><transactionCode>A</transactionCode></transactionCoding>
    <transactionAmounts><transactionShares><value>1000</value></transactionShares>
    <transactionPricePerShare><value>185.50</value></transactionPricePerShare></transactionAmounts>
  </nonDerivativeTransaction></nonDerivativeTable>
</ownershipDocument>"""


def _fake_get_factory(calls: list[str], *, index: dict, xml: str):
    def _fake(url: str, **kw: object) -> _FakeResp:
        calls.append(url)
        if "index.json" in url:
            return _FakeResp(json_data=index)
        return _FakeResp(text=xml)
    return _fake


def test_accession_helpers() -> None:
    assert orch.accession_to_no_dash("0001234567-25-000001") == "000123456725000001"
    assert orch.accession_to_index_url(320193, "0000320193-25-000004") == (
        "https://www.sec.gov/Archives/edgar/data/320193/000032019325000004/index.json"
    )


def test_pick_form4_doc_prefers_xml() -> None:
    idx = {"directory": {"item": [{"name": "a.txt"}, {"name": "primary_doc.xml"}]}}
    assert orch._pick_form4_doc(idx, "x-y-z") == "primary_doc.xml"


def test_pick_form4_doc_fallback_accession_txt() -> None:
    assert orch._pick_form4_doc(_INDEX_TXT_ONLY, "0001234567-25-000001") == "000123456725000001.txt"


def test_pick_form4_doc_empty_returns_none() -> None:
    assert orch._pick_form4_doc({}, "x") is None
    assert orch._pick_form4_doc({"directory": {"item": []}}, "x") is None


def test_fetch_form4_xml_idempotent_cache(monkeypatch, tmp_path) -> None:
    calls: list[str] = []
    monkeypatch.setattr(orch, "_policy_get", _fake_get_factory(calls, index=_INDEX_XML_DOC, xml=_FORM4_XML))
    assert orch.fetch_form4_xml(320193, "0000320193-25-000004", cache_dir=tmp_path) == _FORM4_XML
    assert len(calls) == 2  # index.json + primary_doc.xml
    # second call: cache hit, no new HTTP
    assert orch.fetch_form4_xml(320193, "0000320193-25-000004", cache_dir=tmp_path) == _FORM4_XML
    assert len(calls) == 2


def test_fetch_form4_xml_no_doc_returns_empty(monkeypatch, tmp_path) -> None:
    calls: list[str] = []
    monkeypatch.setattr(orch, "_policy_get", _fake_get_factory(calls, index={"directory": {"item": []}}, xml=_FORM4_XML))
    assert orch.fetch_form4_xml(320193, "0000320193-25-000004", cache_dir=tmp_path) == ""
    assert len(calls) == 1  # only the index fetch


def test_parse_form4_filing_pipeline(monkeypatch, tmp_path) -> None:
    calls: list[str] = []
    monkeypatch.setattr(orch, "_policy_get", _fake_get_factory(calls, index=_INDEX_XML_DOC, xml=_FORM4_XML))
    df = orch.parse_form4_filing(320193, "0000320193-25-000004", cache_dir=tmp_path)
    assert len(df) == 1
    row = df.iloc[0]
    assert row["ticker"] == "AAPL"
    assert row["filer_name"] == "JOHN DOE"
    assert row["acquired_or_disposed"] == "A"
    assert row["shares"] == 1000.0


def test_fetch_form4_transactions_batch(monkeypatch, tmp_path) -> None:
    meta = pd.DataFrame([
        {"issuer_cik": 320193, "filing_date": pd.Timestamp("2024-01-20"), "accession": "A-1-1", "form": "4"},
        {"issuer_cik": 320193, "filing_date": pd.Timestamp("2024-02-01"), "accession": "B-2-2", "form": "4"},
    ])
    monkeypatch.setattr(orch, "fetch_form4_filings", lambda *a, **k: meta)
    monkeypatch.setattr(orch, "_policy_get", _fake_get_factory([], index=_INDEX_XML_DOC, xml=_FORM4_XML))
    df = orch.fetch_form4_transactions(320193, start="2024-01-01", end="2024-12-31", cache_dir=tmp_path)
    assert len(df) == 2  # 2 accessions × 1 transaction each
    assert "accession" in df.columns
    assert set(df["accession"]) == {"A-1-1", "B-2-2"}


def test_fetch_form4_transactions_empty(monkeypatch, tmp_path) -> None:
    empty = pd.DataFrame(columns=["issuer_cik", "filing_date", "accession", "form"])
    monkeypatch.setattr(orch, "fetch_form4_filings", lambda *a, **k: empty)
    df = orch.fetch_form4_transactions(320193, start="2024-01-01", end="2024-12-31", cache_dir=tmp_path)
    assert df.empty
