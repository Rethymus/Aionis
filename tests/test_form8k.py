"""Hermetic tests for the Form 8-K ingest pure functions (fixture-based, no network).

Fixtures are HAND-WRITTEN, labeled, and mimic real EDGAR structures (8-K primary
documents with the three Item spellings seen in the wild; filing index.json file
lists) — no real data, no network, per the project's mock-in-tests-only policy.
Mirrors the testing pattern of ``tests/test_form4.py`` / ``tests/test_form13f.py``.

Covers the three failure modes found during the REAL first pull (2026-08-21,
all reproduced then fixed): the XBRL rendering doc (``R1.htm``) winning the
primary-doc pick, the exhibit with "8-k" in its name winning, the press-release
``q1fy27pr.htm`` winning on shortest-name ties, and the iXBRL thin-space
entities breaking item extraction.
"""
from __future__ import annotations

from aionis.ingest.form8k import (
    _pick_form8k_doc,
    classify_8k,
    extract_8k_items,
)

_ACC = "0000320193-26-000018"


def _idx(names: list[str]) -> dict:
    return {"directory": {"item": [{"name": n} for n in names]}}


# --- extract_8k_items --------------------------------------------------------


def test_extract_items_plain_spelling() -> None:
    doc = "<b>Item 2.02</b> Results of Operations. <b>Item 9.01</b> Exhibits."
    assert extract_8k_items(doc) == ["2.02", "9.01"]


def test_extract_items_nbsp_and_thin_space_entities() -> None:
    doc = "Item&#160;5.02 Item&nbsp;3.01 Item&#8201;8.01 Item&#8202;1.01"
    assert extract_8k_items(doc) == ["1.01", "3.01", "5.02", "8.01"]


def test_extract_items_dedup_sorted_empty() -> None:
    assert extract_8k_items("Item 2.01 Item 2.01") == ["2.01"]
    assert extract_8k_items("") == []
    assert extract_8k_items("no items here") == []


def test_extract_items_ignores_prose_mentions() -> None:
    # "Items and amounts" prose (XBRL render scripts) has no number → no match.
    assert extract_8k_items("function toggle(e){} items and more") == []


# --- classify_8k -------------------------------------------------------------


def test_classify_rare_material_precedence() -> None:
    # 3.01 delisting outranks officer changes and boilerplate exhibits.
    assert classify_8k(["3.01", "5.02", "9.01"]) == "delisting"
    # 2.01 merger completion outranks 5.02.
    assert classify_8k(["2.01", "5.02"]) == "merger_completion"


def test_classify_unmapped_and_unclassified() -> None:
    assert classify_8k(["6.02", "6.05"]) == "other"  # ABS items exist, no mapping
    assert classify_8k([]) == "unclassified"  # honest miss, never guessed


def test_classify_known_categories() -> None:
    assert classify_8k(["5.02"]) == "officer_changes"
    assert classify_8k(["2.02", "9.01"]) == "results"
    assert classify_8k(["1.01", "2.03", "7.01"]) == "financial_obligation"


# --- _pick_form8k_doc (scored primary-doc selection) -------------------------


def test_pick_prefers_explicit_8k_over_xbrl_rendering() -> None:
    names = ["R1.htm", "d171253d8k.htm", "report.css", "Show.js"]
    assert _pick_form8k_doc(_idx(names), _ACC) == "d171253d8k.htm"


def test_pick_exhibit_with_8k_name_loses_to_issuer_date_doc() -> None:
    # REAL failure: Apple earnings 8-K — exhibit a8-kex991q3... beat the true
    # primary aapl-20260730.htm because "8-k" appeared inside the exhibit name.
    names = [
        "0000320193-26-000018-index.html",
        "a8-kex991q3202606272026.htm",
        "aapl-20260730.htm",
        "R1.htm",
    ]
    assert _pick_form8k_doc(_idx(names), _ACC) == "aapl-20260730.htm"


def test_pick_issuer_date_doc_beats_press_release() -> None:
    # REAL failure: NVDA — press-release exhibit q1fy27pr.htm won a score-1 tie
    # on shortest name before the issuer-date convention was scored 0.
    names = ["q1fy27pr.htm", "nvda-20260520.htm"]
    assert _pick_form8k_doc(_idx(names), _ACC) == "nvda-20260520.htm"


def test_pick_falls_back_to_accession_txt() -> None:
    names = ["0000320193-26-000018-index.html"]
    assert _pick_form8k_doc(_idx(names), _ACC) is None
    names = ["000032019326000018.txt", "0000320193-26-000018-index.html"]
    assert _pick_form8k_doc(_idx(names), _ACC) == "000032019326000018.txt"


def test_pick_handles_legacy_items_schema() -> None:
    idx = {"items": [{"name": "a2q1form8-k.htm"}, {"name": "ex991.htm"}]}
    assert _pick_form8k_doc(idx, _ACC) == "a2q1form8-k.htm"
