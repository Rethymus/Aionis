"""Hermetic tests for the DEF 14A person-level parser (fixtures, no network).

Fixtures are HAND-WRITTEN, labeled, and mimic the two real EDGAR layouts the
first live pull (2026-08-23) hit: row-intact tables ("Name (Age) Title Since")
and word-fragmented inline-XBRL documents where every word rides its own
``<div>`` (the stream pass reconstructs rows by age anchors). No real data, no
network — mirrors ``tests/test_form8k.py``.
"""
from __future__ import annotations

from aionis.ingest.def14a_persons import (
    _pick_def14a_doc,
    _roles_in_line,
    parse_def14a_persons,
)

_ACC = "0001683168-26-006660"

# --- row-intact layout --------------------------------------------------------


def test_row_intact_roster_parses_with_roles() -> None:
    doc = """
    <h2>Information about our Directors and Executive Officers</h2>
    <table>
      <tr><td>John A. Smith (58)</td><td>Chief Executive Officer and Director since 2019</td></tr>
      <tr><td>Mary Jones (47)</td><td>Chief Financial Officer</td></tr>
      <tr><td>Robert Chen (62)</td><td>Director</td></tr>
    </table>
    """
    r = parse_def14a_persons(doc)
    assert r["parsed"] is True
    assert r["method"] == "section_age_rows"
    got = {p["name"]: p["roles"] for p in r["persons"]}
    assert got["John A. Smith"] == ["ceo", "director"]
    assert got["Mary Jones"] == ["cfo"]
    assert got["Robert Chen"] == ["director"]


def test_fragmented_layout_recovered_by_stream_pass() -> None:
    # REAL failure mode (Venu Holding 2026-08-23): every word its own div —
    # a table row never survives as one line; the age anchors must delimit
    # the rows in the joined stream.
    doc = """
    <div>Information</div><div>about</div><div>our</div><div>Directors</div>
    <div>Steve</div><div>Cominsky</div><div>56</div><div>Director</div>
    <div>David</div><div>Lavigne</div><div>64</div><div>Director</div>
    """
    r = parse_def14a_persons(doc)
    assert r["parsed"] is True
    got = {p["name"]: p["roles"] for p in r["persons"]}
    assert got == {"Steve Cominsky": ["director"], "David Lavigne": ["director"]}


def test_title_prefix_stripped_from_name_span() -> None:
    # "Chief Financial Officer Heather Atkinson (45)" — the greedy name span
    # absorbs the preceding title; the title tokens must be stripped.
    doc = (
        "<p>Directors and Executive Officers</p>"
        "<p>Chief Financial Officer Heather Atkinson (45) since 2021</p>"
    )
    r = parse_def14a_persons(doc)
    assert [p["name"] for p in r["persons"]] == ["Heather Atkinson"]
    assert r["persons"][0]["roles"] == ["cfo"]


# --- honest-null discipline (never guess) -------------------------------------


def test_no_section_means_honest_null() -> None:
    # Names + ages + roles exist but NO directors/executives section heading:
    # nothing opens a window, nothing is extracted — never a heuristic guess.
    doc = "<p>John A. Smith (58) Chief Executive Officer</p>"
    r = parse_def14a_persons(doc)
    assert r == {"persons": [], "parsed": False, "method": ""}


def test_name_without_role_word_not_extracted() -> None:
    # A name + age inside a section but NO role word on the row: dropped —
    # every shipped person must carry a witnessed role word.
    doc = (
        "<p>Directors and Executive Officers</p>"
        "<p>John A. Smith (58) joined the Company in 2019</p>"
    )
    r = parse_def14a_persons(doc)
    assert r["parsed"] is False


def test_toc_stream_yields_nothing() -> None:
    # TOC lines ("Directors and Executive Officers 33") open windows but
    # carry stopworded spans, not people.
    doc = (
        "<p>directors and executive officers 33 director and executive "
        "compensation 35 risk factors 8 security ownership of management 42</p>"
    )
    r = parse_def14a_persons(doc)
    assert r["parsed"] is False


def test_age_bounds_reject_implausible_ages() -> None:
    doc = (
        "<p>Our Executive Officers of the Company</p>"
        "<p>John Smith (29) Director</p><p>Jane Doe (45) Director</p>"
    )
    r = parse_def14a_persons(doc)
    assert [p["name"] for p in r["persons"]] == ["Jane Doe"]


def test_empty_and_blank_documents() -> None:
    assert parse_def14a_persons("") == {"persons": [], "parsed": False, "method": ""}
    assert parse_def14a_persons("<html><body></body></html>")["parsed"] is False


# --- role vocabulary guards ----------------------------------------------------


def test_advisor_to_ceo_is_not_a_ceo() -> None:
    # "Advisor to Chief Executive Officer" — a guarded chief-role must not
    # grant ceo (the external/past title discipline).
    roles = _roles_in_line("Director Nominee and Advisor to Chief Executive Officer")
    assert "ceo" not in roles
    assert "director" in roles


def test_vice_president_not_plain_president() -> None:
    roles = _roles_in_line("Executive Vice President and Treasurer")
    assert "president" not in roles
    assert "vice_president" in roles and "treasurer" in roles


# --- _pick_def14a_doc (scored primary-doc selection) --------------------------


def _idx(names: list[str]) -> dict:
    return {"directory": {"item": [{"name": n} for n in names]}}


def test_pick_prefers_def14a_over_rendering_and_exhibits() -> None:
    names = ["R1.htm", "formdef14a.htm", "ex991.htm", "graphic.jpg"]
    assert _pick_def14a_doc(_idx(names), _ACC) == "formdef14a.htm"


def test_pick_issuer_date_doc_beats_generic_htm() -> None:
    names = ["cover.htm", "cns-20260815.htm"]
    assert _pick_def14a_doc(_idx(names), _ACC) == "cns-20260815.htm"


def test_pick_exhibit_with_14a_in_name_loses() -> None:
    names = ["ex14a1.htm", "proxy2026.htm"]
    assert _pick_def14a_doc(_idx(names), _ACC) == "proxy2026.htm"


def test_pick_falls_back_to_accession_txt() -> None:
    names = [f"{_ACC.replace('-', '')}.txt", "index.html"]
    assert _pick_def14a_doc(_idx(names), _ACC) == _ACC.replace("-", "") + ".txt"
    assert _pick_def14a_doc(_idx(["index.html"]), _ACC) is None
