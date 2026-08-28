"""TASK-DISP-D contract tests — DEF 14A person-name denoising.

Bug (verified on the 2026-08-23 cache): the greedy age anchors absorbed the
proxy roster's capitalized age-column header onto captured names, splitting
one real person into a clean and an "... Age"-suffixed identity — e.g.
"Charles M. Chiappone Age" / "John B. Blystone Age" / "Mark C. Davis Age"
sat next to their clean twins in the exported top_persons (3 of 50), and the
lineage graph built phantom co_board edges between a person and their own
suffix twin (12 edges around the Worthington cluster pre-fix, 6 real ones
post-fix). These tests pin: (1) the parser strips ONLY the provable
structural tail "<Age-token> <2-3 digit age>"; (2) the committed export and
its lineage derivative carry no dirty names and consistent merged entries.
Hermetic: parser tests are pure functions; artifact tests read tracked JSONs.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from aionis.ingest.def14a_persons import (
    cleanse_cached_person_rows,
    parse_def14a_persons,
    strip_cached_bare_age_tail,
)

# export_terminal_data.py uses a sibling import (``import export_quarto_data``),
# so it must be imported with scripts/ on sys.path (the
# tests/test_export_terminal_data.py pattern).
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import export_terminal_data as etd  # noqa: E402

DATA = Path("web/src/data/aionis")
_SECTION = "<h2>Directors and Executive Officers</h2>"

# The three bug-evidence strings from the 2026-08-25 export (pinning these
# exact strings is ALLOWED by the task spec — they are the empirical bug).
_DIRTY_TRIO = ("Charles M. Chiappone Age", "John B. Blystone Age", "Mark C. Davis Age")
_CLEAN_TRIO = ("Charles M. Chiappone", "John B. Blystone", "Mark C. Davis")


def _persons(html: str) -> list[dict]:
    return parse_def14a_persons(_SECTION + html)["persons"]


# --- parser layer: structural-tail stripping ---------------------------------


def test_word_anchor_age_header_stripped() -> None:
    """'Name Age NN' inline-header spelling -> exactly ONE clean person."""
    out = _persons("<p>Mark C. Davis Age 64 Chairman of the Board</p>")
    assert [(p["name"], p["roles"]) for p in out] == [
        ("Mark C. Davis", ["chairman"]),
    ]


def test_paren_anchor_absorbed_age_header_stripped() -> None:
    """Absorbed header even before the parenthesized age: 'Age (63)'."""
    out = _persons(
        "<p>Charles M. Chiappone Age (63) Chief Executive Officer "
        "and President</p>",
    )
    assert [p["name"] for p in out] == ["Charles M. Chiappone"]
    assert out[0]["roles"] == ["ceo", "president"]


def test_known_trio_spellings_normalize_to_clean_names() -> None:
    docs = (
        "<p>John B. Blystone Age 77 Director since 2019</p>",
        "<table><tr><td>Charles M. Chiappone Age</td><td>(63)</td>"
        "<td>President</td></tr></table>",
        "<div>Mark</div><div>C.</div><div>Davis</div><div>Age</div>"
        "<div>64</div><div>Director</div>",
    )
    got = {p["name"] for doc in docs for p in _persons(doc)}
    assert got == {"John B. Blystone", "Charles M. Chiappone", "Mark C. Davis"}


def test_clean_and_dirty_variants_merge_with_roles_unioned() -> None:
    """One real person witnessed twice (clean + glued spellings) collapses
    into ONE entry carrying the UNION of the row roles — the merge must not
    lose either witness."""
    out = _persons(
        "<p>Mary J. Roe, age 58, Chief Financial Officer</p>"
        "<p>Mary J. Roe Age 58 Director of the Company</p>",
    )
    assert len(out) == 1
    assert out[0]["name"] == "Mary J. Roe"
    assert out[0]["roles"] == ["cfo", "director"]


def test_bare_age_without_digits_is_not_stripped() -> None:
    """NO fuzzy matching: a middle-initial name followed by the bare word
    'Age' with NO witnessed digit run is NOT provably structural — kept as
    captured (the token could be someone's surname; 宁可保留不猜测)."""
    out = _persons("<p>Bob J. Smith Age Director since 2010</p>")
    assert [p["name"] for p in out] == ["Bob J. Smith Age"]


def test_one_token_remnant_is_dropped_not_shipped() -> None:
    """'<X> Age NN' whose strip leaves a single non-name token was never a
    plausible personal name — dropped entirely, never shipped to display."""
    out = _persons("<p>One Age 63 Director since 2015</p>")
    assert out == []


def test_clean_rows_are_byte_untouched_by_denoise() -> None:
    """Regression guard: documents WITHOUT the glue parse identically to the
    pre-fix contract (names, roles, tier all unchanged)."""
    doc = (
        "<table><tr><td>John A. Smith (58)</td>"
        "<td>Chief Executive Officer and Director since 2019</td></tr></table>"
        "<p>Jane R. Doe, 45, Secretary</p>"
        "<p>Peter Q. Principal age 62 Treasurer</p>"
    )
    r = parse_def14a_persons(_SECTION + doc)
    assert r["method"] == "section_age_rows"
    assert r["parsed"] is True
    got = {p["name"]: p["roles"] for p in r["persons"]}
    assert got == {
        "John A. Smith": ["ceo", "director"],
        "Jane R. Doe": ["secretary"],
        "Peter Q. Principal": ["treasurer"],
    }


# --- consumption layer: stale PRE-fix cache rows (TASK-DISP-X) ---------------
#
# The parse cache (data/cache/def14a_persons_parsed.json) predates the
# structural-age-tail fix, so its ok-rows still carry bare-Age-tailed names
# that the current parse rule can no longer produce; a window slide re-admits
# them into the exported panel. These tests pin the CONSUMPTION-layer cleanse:
# strip only on proof (a witnessed `age` field on the row, or the clean twin
# of the split identity witnessed in the panel), keep otherwise, never mint a
# sub-name, and re-merge twin rows so assembly does not double-count seats.


def test_cached_bare_age_with_witnessed_age_field_stripped() -> None:
    """A cached row carrying the anchor's digit run (non-null ``age`` field)
    has its bare ``Age`` tail deterministically stripped; roles survive."""
    row = {"name": "John B. Blystone Age", "roles": ["director"], "age": 77}
    assert cleanse_cached_person_rows([row]) == [
        {"name": "John B. Blystone", "roles": ["director"], "age": 77},
    ]
    # Case variants of the tail token strip identically.
    assert strip_cached_bare_age_tail("Mark C. Davis AGE", witnessed_age=64) == (
        "Mark C. Davis"
    )


def test_cached_bare_age_without_witness_is_kept() -> None:
    """No ``age`` field and no clean twin in the panel keys -> the row ships
    as captured (the tail could be a surname; 宁可保留不猜测) — the
    consumption mirror of test_bare_age_without_digits_is_not_stripped."""
    row = {"name": "Bob J. Smith Age", "roles": ["director"]}
    assert cleanse_cached_person_rows([row]) == [row]
    assert strip_cached_bare_age_tail("Bob J. Smith Age") is None


def test_cached_twin_witness_merges_split_identity() -> None:
    """The clean twin in the filing witnesses the tail as the absorbed header:
    the rows re-merge into ONE identity carrying the roles union (never two
    rows / two seats for one real person at one company)."""
    rows = [
        {"name": "Charles M. Chiappone", "roles": ["director"]},
        {"name": "Charles M. Chiappone Age", "roles": ["director", "ceo"]},
    ]
    assert cleanse_cached_person_rows(rows) == [
        {"name": "Charles M. Chiappone", "roles": ["ceo", "director"]},
    ]


def test_cached_normal_names_untouched_and_no_subname_minted() -> None:
    """Clean names pass through byte-identical, and cleansing never strips
    down to a one-token remnant ('One Age' is kept, not reduced to 'One')."""
    rows = [
        {"name": "Mary J. Roe", "roles": ["cfo"]},
        {"name": "One Age", "roles": ["director"]},
    ]
    assert cleanse_cached_person_rows(rows) == rows


def test_cached_cleanse_is_idempotent() -> None:
    """cleanse(cleanse(rows)) == cleanse(rows): a cleansed panel re-enters
    the cleanse unchanged."""
    dirty = [
        {"name": "John B. Blystone Age", "roles": ["director"]},
        {"name": "John B. Blystone", "roles": ["director"]},
        {"name": "Mark C. Davis Age", "roles": ["director"]},
        {"name": "Mark C. Davis", "roles": ["director"]},
    ]
    once = cleanse_cached_person_rows(dirty)
    assert [r["name"] for r in once] == ["John B. Blystone", "Mark C. Davis"]
    assert cleanse_cached_person_rows(once) == once


def test_assembly_cleanse_stale_cache_trio(tmp_path, monkeypatch) -> None:
    """Assembly-level: stale PRE-fix cache rows carrying the Chiappone /
    Blystone / Davis dirty forms are cleansed when the cache assembles into
    the panel — the exported payload ships no ' Age'-tailed name, each trio
    member merges into its clean twin's two-board entry, and the clean twin +
    stripped-twin pair counts ONE seat per company."""
    web = tmp_path / "web" / "src" / "data" / "aionis"
    web.mkdir(parents=True)
    monkeypatch.setattr(etd, "WEB", web)
    cache_dir = tmp_path / "data" / "cache"
    cache_dir.mkdir(parents=True)
    filings = {
        "0001193125-26-352256": {
            "company": "WORTHINGTON ENTERPRISES, INC.",
            "ticker": "WOR",
            "issuer_cik": "1093815",
            "filed_date": "2026-07-28",
            "parsed": True,
            "method": "section_age_rows",
            "persons": [
                {"name": "John H. McConnell II", "roles": ["chairman"]},
                {"name": "Charles M. Chiappone", "roles": ["director"]},
                {"name": "Charles M. Chiappone Age", "roles": ["director"]},
                {"name": "John B. Blystone", "roles": ["director"]},
                {"name": "Mark C. Davis", "roles": ["director"]},
            ],
        },
        "0001193125-26-348765": {
            "company": "Worthington Steel, Inc.",
            "ticker": "WS",
            "issuer_cik": "1967512",
            "filed_date": "2026-08-04",
            "parsed": True,
            "method": "section_age_rows",
            "persons": [
                {"name": "Charles M. Chiappone Age", "roles": ["director"]},
                {"name": "John B. Blystone Age", "roles": ["director"]},
                {"name": "Mark C. Davis Age", "roles": ["director"]},
            ],
        },
    }
    (cache_dir / "def14a_persons_parsed.json").write_text(json.dumps({
        "fetched_at": "2026-08-23T15:36:40+00:00",
        "n_target": 2,
        "n_processed": 2,
        "n_with_persons": 2,
        "budget_seconds": 2700,
        "budget_hit": False,
        "n_requests": 0,
        "results": filings,
    }), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    etd.export_def14a_persons()
    payload = json.loads((web / "def14a_persons.json").read_text())
    names = [e["name"] for e in payload["top_persons"]]
    assert all(not re.search(r"\s[Aa][Gg][Ee]$", n) for n in names)
    for dirty in _DIRTY_TRIO:
        assert dirty not in names, f"dirty identity shipped: {dirty}"
    by_name = {e["name"]: e for e in payload["top_persons"]}
    assert "John H. McConnell II" in by_name  # clean control untouched
    for clean in _CLEAN_TRIO:
        e = by_name[clean]
        assert e["n_companies"] == 2, clean
        assert sorted(e["companies"]) == [
            "WORTHINGTON ENTERPRISES, INC.",
            "Worthington Steel, Inc.",
        ]
        assert set(e["roles"]) & {"director"}, clean
    by_ticker = {b["ticker"]: b for b in payload["boards"]}
    assert by_ticker["WOR"]["n_persons"] == 4  # 5 cached rows, twin pair merged
    assert by_ticker["WS"]["n_persons"] == 3


# --- artifact layer: committed export + derived lineage ----------------------


def test_no_exported_name_has_age_suffix() -> None:
    payload = json.loads((DATA / "def14a_persons.json").read_text())
    for entry in payload.get("top_persons") or []:
        assert not re.search(r"\s[Aa][Gg][Ee]$", entry["name"]), entry["name"]


def test_known_dirty_trio_fixed_in_export() -> None:
    payload = json.loads((DATA / "def14a_persons.json").read_text())
    names = [e["name"] for e in payload["top_persons"]]
    for dirty in _DIRTY_TRIO:
        assert dirty not in names, f"dirty identity shipped: {dirty}"
    by_name = {e["name"]: e for e in payload["top_persons"]}
    # Same real persons, now merged single entries at the same two boards.
    for clean in _CLEAN_TRIO:
        assert clean in by_name, f"merged entry missing: {clean}"
        e = by_name[clean]
        assert sorted(e["companies"]) == [
            "WORTHINGTON ENTERPRISES, INC.",
            "Worthington Steel, Inc.",
        ]
        assert e["n_companies"] == 2
        assert set(e["roles"]) & {"director"}, clean


def test_lineage_has_no_dirty_person_nodes() -> None:
    lg = json.loads((DATA / "lineage_graph.json").read_text())
    labels = [
        n["id"][2:] for n in lg["nodes"]
        if n["id"].startswith("p:")
    ]
    for dirty in _DIRTY_TRIO:
        assert dirty.upper() not in labels, f"dirty node: {dirty}"


def test_lineage_worthington_cluster_edges_consistent() -> None:
    """The Worthington cluster post-fix: co_board edges run between CLEAN
    person ids only, no edge touches an Age-suffixed id, and each real pair
    keeps its w=2 weight (two shared boards: WOR + WS)."""
    lg = json.loads((DATA / "lineage_graph.json").read_text())
    trio_upper = {d.upper() for d in _DIRTY_TRIO}
    cluster = []
    for e in lg["edges"]:
        if e["type"] != "co_board":
            continue
        touched = {e["a"].upper(), e["b"].upper()}
        assert not (touched & trio_upper), f"edge references dirty id: {e}"
        if any("WORTHINGTON" in json.dumps(s) for s in e.get("shared") or []):
            cluster.append(e)
    pairs = {(e["a"], e["b"]) for e in cluster}
    assert pairs == {
        ("p:CHARLES M. CHIAPPONE", "p:JOHN B. BLYSTONE"),
        ("p:CHARLES M. CHIAPPONE", "p:JOHN H. MCCONNELL II"),
        ("p:CHARLES M. CHIAPPONE", "p:MARK C. DAVIS"),
        ("p:JOHN B. BLYSTONE", "p:JOHN H. MCCONNELL II"),
        ("p:JOHN B. BLYSTONE", "p:MARK C. DAVIS"),
        ("p:JOHN H. MCCONNELL II", "p:MARK C. DAVIS"),
    }
    assert all(e["w"] == 2 for e in cluster)
