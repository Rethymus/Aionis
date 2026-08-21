"""IPO registration/pricing stream — hermetic (no network).

Pins :mod:`aionis.ingest.form_ipo`: the EFTS query is FORM-LEVEL (whole
market — NO ``ciks=`` parameter, unlike form4/form8k; IPO filers are not a
known universe); the root form ``S-1`` expands to S-1/A; status is derived
from the immutable form type (S-1 family → ``filed``, 424B4 → ``priced``);
the ticker is parsed from ``display_names`` (EFTS ``display_symbols`` is null
on every live-probed hit) and stays honestly empty for pre-symbol filers;
rows are per-accession, deduplicated across the two root-form queries and
sorted newest-first; each row links the EDGAR filing-index page (offer terms
are inside the prospectus documents — v1 does not parse them).

Fixtures are HAND-WRITTEN and mimic the verified live EFTS response shape
(2026-08-22 probe, e.g. ``"Aptera Motors Corp  (SEV)  (CIK 0001786471)"``) —
no real data, no network, per the project's mock-in-tests-only policy.
Mirrors the offline pattern of ``tests/test_stakes_13d_efts.py``.
"""
from __future__ import annotations

import json

import pytest
import requests

from aionis.ingest import form_ipo, universe
from aionis.ingest.http_policy import HttpRequestPolicy

START, END = "2026-04-25", "2026-08-22"


class _Resp:
    def __init__(self, payload, status_code=200):
        self._p = payload
        self.status_code = status_code
        self.headers = {}

    def json(self): return self._p


def _src(
    cik: int, name: str, adsh: str, date: str, form: str,
) -> dict:
    """One efts ``_source`` shaped like the verified live response."""
    return {
        "ciks": [f"{cik:010d}"],
        "display_names": [name],
        "display_symbols": None,  # null on every live-probed hit
        "file_date": date,
        "form": form,
        "adsh": adsh,
        "root_forms": [form.split("/")[0]],
    }


def _efts(sources, total=None):
    n = total if total is not None else len(sources)
    hits = [{"_index": "edgar", "_id": s.get("adsh", ""), "_score": 1.0, "_source": s}
            for s in sources]
    return {"took": 1, "timed_out": False, "_shards": {}, "hits": {
        "total": {"value": n, "relation": "eq"}, "hits": hits,
    }}


def _install_policy(monkeypatch, sleeps=None):
    now = [0.0]

    def sleep(seconds):
        if sleeps is not None:
            sleeps.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(
        universe,
        "_HTTP_POLICY",
        HttpRequestPolicy(
            clock=lambda: now[0],
            sleeper=sleep,
            retry_exceptions=(requests.RequestException,),
        ),
    )


def _no_network(monkeypatch, url_map, sleeps=None):
    """Serve a URL map through the shared policy with fake time."""
    calls: list[str] = []

    def fake(url, headers=None, timeout=None):
        calls.append(url)
        if url in url_map:
            return _Resp(url_map[url])
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(requests, "get", fake)
    _install_policy(monkeypatch, sleeps)
    return calls


def _fetch(cache_dir):
    return form_ipo.fetch_ipo_filings(start=START, end=END, cache_dir=cache_dir)


# --- verified query shape (form-level, NO ciks) ------------------------------


def test_url_is_form_level_without_ciks():
    """Pin the verified efts query: FORM-level (whole market — no ``ciks=``,
    unlike form4/form8k per-issuer queries), root form, custom date range."""
    url = form_ipo._efts_url("S-1", START, END, 0)
    assert "ciks=" not in url, "IPO query must be whole-market (no CIK filter)"
    assert "forms=S-1" in url                 # root form; expands to S-1/A
    assert "dateRange=custom" in url
    assert f"startdt={START}" in url and f"enddt={END}" in url
    assert "from=0" in url
    assert "424B4" in form_ipo._efts_url("424B4", START, END, 0)


# --- status derivation (form type → stage marker) ----------------------------


def test_status_derivation():
    assert form_ipo.ipo_status("S-1") == "filed"
    assert form_ipo.ipo_status("S-1/A") == "filed"      # amendment = new filing
    assert form_ipo.ipo_status("424B4") == "priced"     # final prospectus
    assert form_ipo.ipo_status("S-3") == ""             # defense-in-depth drop
    assert form_ipo.ipo_status("") == ""


# --- display-name parsing -----------------------------------------------------


def test_parse_company_with_and_without_ticker():
    with_tk = ["Aptera Motors Corp  (SEV)  (CIK 0001786471)"]
    assert form_ipo._parse_company(with_tk) == "Aptera Motors Corp"
    no_tk = ["Orion180 Insurance Group Inc  (CIK 0002124472)"]
    assert form_ipo._parse_company(no_tk) == "Orion180 Insurance Group Inc"
    assert form_ipo._parse_company(None) == ""


def test_parse_ticker_from_display_names():
    assert form_ipo.parse_ticker(["Aptera Motors Corp  (SEV)  (CIK 0001786471)"]) == "SEV"
    # Pre-symbol S-1 filer: only the CIK group — honest empty, never guessed.
    assert form_ipo.parse_ticker(["Acme Holdings  (CIK 0001234567)"]) == ""
    assert form_ipo.parse_ticker(None) == ""


# --- pipeline (both root forms, dedup, order, urls) --------------------------


def test_fetch_assembles_both_forms_with_status_and_order(monkeypatch, tmp_path):
    s1_url = form_ipo._efts_url("S-1", START, END, 0)
    p4_url = form_ipo._efts_url("424B4", START, END, 0)
    url_map = {
        s1_url: _efts([
            _src(1553788, "SPLASH BEVERAGE GROUP, INC.  (SBEV)  (CIK 0001553788)",
                 "0001731122-26-001117", "2026-08-20", "S-1/A"),
            _src(2124472, "Orion180 Insurance Group Inc  (CIK 0002124472)",
                 "0001628280-26-058231", "2026-07-10", "S-1"),
        ]),
        p4_url: _efts([
            _src(1786471, "Aptera Motors Corp  (SEV)  (CIK 0001786471)",
                 "0001493152-26-039508", "2026-08-21", "424B4"),
        ]),
    }
    _no_network(monkeypatch, url_map)

    df = _fetch(tmp_path)

    assert list(df["accession"]) == [
        "0001493152-26-039508", "0001731122-26-001117", "0001628280-26-058231",
    ], "rows must be newest-first"
    assert list(df["status"]) == ["priced", "filed", "filed"]
    assert list(df["form"]) == ["424B4", "S-1/A", "S-1"]
    assert df["ticker"].tolist()[0] == "SEV"
    assert df["ticker"].tolist()[2] == "", "pre-symbol S-1 filer stays empty"
    assert df["company"].tolist()[1] == "SPLASH BEVERAGE GROUP, INC."


def test_fetch_doc_url_is_filing_index_link(monkeypatch, tmp_path):
    """v1 honest choice: link the EDGAR filing-index page (zero extra requests)
    instead of resolving the primary doc (~1,000 index.json fetches)."""
    s1_url = form_ipo._efts_url("S-1", START, END, 0)
    _no_network(monkeypatch, {
        s1_url: _efts([_src(1786471, "Aptera Motors Corp  (SEV)  (CIK 0001786471)",
                            "0001493152-26-039508", "2026-08-20", "424B4")]),
        form_ipo._efts_url("424B4", START, END, 0): _efts([]),
    })

    df = _fetch(tmp_path)

    assert df["doc_url"].iloc[0] == (
        "https://www.sec.gov/Archives/edgar/data/1786471/"
        "000149315226039508/0001493152-26-039508-index.htm"
    )


def test_fetch_dedups_accession_across_root_forms(monkeypatch, tmp_path):
    """The same accession must survive once even if both root-form queries
    returned it (defense-in-depth; the live queries do not overlap)."""
    dup = _src(1786471, "Aptera Motors Corp  (SEV)  (CIK 0001786471)",
               "0001493152-26-039508", "2026-08-20", "424B4")
    _no_network(monkeypatch, {
        form_ipo._efts_url("S-1", START, END, 0): _efts([dup]),
        form_ipo._efts_url("424B4", START, END, 0): _efts([dup]),
    })

    df = _fetch(tmp_path)

    assert len(df) == 1
    assert df["accession"].duplicated().sum() == 0


def test_fetch_filters_out_of_window(monkeypatch, tmp_path):
    """efts bounds server-side; the row filter is defense-in-depth."""
    _no_network(monkeypatch, {
        form_ipo._efts_url("S-1", START, END, 0): _efts([
            _src(1, "Old Co  (CIK 0000000001)", "PRE", "2026-01-01", "S-1"),
            _src(2, "In Co  (CIK 0000000002)", "IN", "2026-06-01", "S-1"),
            _src(3, "Future Co  (CIK 0000000003)", "POST", "2027-01-01", "S-1"),
        ]),
        form_ipo._efts_url("424B4", START, END, 0): _efts([]),
    })

    df = _fetch(tmp_path)

    assert list(df["accession"]) == ["IN"]


# --- pagination ---------------------------------------------------------------


def test_paginates_across_from_pages(monkeypatch, tmp_path):
    """A root form with >100 hits paginates via ``from=`` (live: S-1 family =
    827 → 9 pages). _PAGE_SIZE shrunk to 2 to exercise the walk hermetically."""
    monkeypatch.setattr(form_ipo, "_PAGE_SIZE", 2)

    def mk(a: str, d: str) -> dict:
        return _src(1, f"Co {a}  (CIK 0000000001)", a, d, "S-1")

    hits1 = [mk("A", "2026-05-01"), mk("B", "2026-05-02")]
    hits2 = [mk("C", "2026-05-03")]
    calls = _no_network(monkeypatch, {
        form_ipo._efts_url("S-1", START, END, 0): _efts(hits1, total=3),
        form_ipo._efts_url("S-1", START, END, 2): _efts(hits2, total=3),
        form_ipo._efts_url("424B4", START, END, 0): _efts([]),
    })

    df = _fetch(tmp_path)

    assert set(df["accession"]) == {"A", "B", "C"}
    assert form_ipo._efts_url("S-1", START, END, 2) in calls


# --- cache --------------------------------------------------------------------


def test_cache_hit_makes_no_call(monkeypatch, tmp_path):
    (tmp_path / f"efts_ipo_S-1_{START}_{END}.json").write_text(json.dumps([
        _src(1786471, "Acme Holdings  (CIK 0001786471)",
             "0001493152-26-000001", "2026-08-20", "S-1"),
    ]))
    (tmp_path / f"efts_ipo_424B4_{START}_{END}.json").write_text(json.dumps([
        _src(1786471, "Aptera Motors Corp  (SEV)  (CIK 0001786471)",
             "0001493152-26-039508", "2026-08-20", "424B4"),
    ]))
    _no_network(monkeypatch, {})  # empty map -> any call raises

    df = _fetch(tmp_path)

    assert len(df) == 2


def test_permanent_4xx_fails_fast(monkeypatch, tmp_path):
    sleeps: list[float] = []
    calls = {"n": 0}

    def fake(url, headers=None, timeout=None):
        calls["n"] += 1
        return _Resp(None, status_code=404)

    monkeypatch.setattr(requests, "get", fake)
    _install_policy(monkeypatch, sleeps)

    with pytest.raises(RuntimeError, match="404"):
        _fetch(tmp_path)
    assert calls["n"] == 1
    assert sleeps == []


# --- empty is safe ------------------------------------------------------------


def test_fetch_empty_is_safe(monkeypatch, tmp_path):
    _no_network(monkeypatch, {
        form_ipo._efts_url("S-1", START, END, 0): _efts([]),
        form_ipo._efts_url("424B4", START, END, 0): _efts([]),
    })
    df = _fetch(tmp_path)
    assert df.empty
    assert list(df.columns) == [
        "issuer_cik", "company", "ticker", "filed_date",
        "form", "status", "accession", "doc_url",
    ]
