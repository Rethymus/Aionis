"""Contract tests for the knowledge-shelf panel (web/src/data/aionis/).

The /shelf page renders this catalog — the web build environment has no repo
files, so the panel JSON must carry its own complete bibliography (metadata +
safe teaser slices + GitHub link-outs) and the fixed curated research-source
bookmarks. Pure checks on tracked artifacts (hermetic, no network, no
runs/cache dependency), plus unit locks on the exporter's pure helpers
(category whitelist, teaser mining) with hand-written fixtures.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

DATA = Path("web/src/data/aionis")
sys.path.insert(0, str(Path("scripts").resolve()))
import export_terminal_data as et  # noqa: E402

# The shelf's fixed 5-rail category whitelist (mirror of _KS_CATEGORIES).
CATEGORIES = {"preregistration", "adr", "results", "rubric", "theory"}
_GITHUB = "https://github.com/Rethymus/Aionis/blob/main/"
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
# Teaser contract: first 2-3 sentences, hard-capped at 240 chars (the "…"
# ellipsis may push the truncated form to 241).
_MAX_TEASER = 241
# Layer 3: the fixed evidence-artifact ids (pinned — a new artifact is a new
# catalog entry + a new id, never a rename of these).
ARTIFACT_IDS = {"atlas-claim-v1", "research-dossier-v1"}
_DICT = Path("web/src/i18n/dict.ts")


def _load() -> dict:
    return json.loads((DATA / "knowledge_shelf.json").read_text(encoding="utf-8"))


# --- panel contract (tracked JSON) --------------------------------------------


def test_knowledge_shelf_category_whitelist_and_reconciliation() -> None:
    """Categories are the fixed 5-rail whitelist and n_docs reconciles."""
    ks = _load()
    assert ks["status"] == "ok"
    assert set(ks["categories"]) == CATEGORIES, "category rails must be the fixed 5"
    for n in ks["categories"].values():
        assert isinstance(n, int) and n >= 0
    assert sum(ks["categories"].values()) == len(ks["docs"]), "rail counts must sum to n_docs"
    assert ks["n_docs"] == len(ks["docs"]), "n_docs must equal len(docs)"
    assert ks["n_categories"] == sum(1 for n in ks["categories"].values() if n)
    for d in ks["docs"]:
        assert d["category"] in CATEGORIES, f"unknown category {d['category']!r}"


def test_knowledge_shelf_every_doc_has_title_path_summary() -> None:
    """Every catalog entry carries title/path/summary; paths resolve in-repo."""
    ks = _load()
    assert len(ks["docs"]) >= 50, "the shelf must catalog the whole method library"
    for d in ks["docs"]:
        assert isinstance(d["title"], str) and d["title"].strip(), d
        assert isinstance(d["summary"], str) and d["summary"].strip(), d["path"]
        assert d["path"].startswith(("docs/", "decisions/")), d["path"]
        assert Path(d["path"]).exists(), f"{d['path']} renamed without re-export"
        assert isinstance(d["n_chars"], int) and d["n_chars"] > 0
        # Full text stays on GitHub — the card links out, never copies.
        assert d["url"] == _GITHUB + d["path"], d["path"]
        # Safe teaser slice, never a content copy.
        assert len(d["summary"]) <= _MAX_TEASER, d["path"]


def test_knowledge_shelf_date_format_and_as_of() -> None:
    """Dates are last-commit YYYY-MM-DD; as_of is the newest of them."""
    ks = _load()
    dates = []
    for d in ks["docs"]:
        assert d["date"] is None or _DATE.fullmatch(d["date"]), d["date"]
        if d["date"]:
            dates.append(d["date"])
    assert dates, "inside the repo every doc must carry a git date"
    assert ks["as_of"] == max(dates), "as_of must be the newest doc commit date"


def test_knowledge_shelf_curated_research_sources() -> None:
    """The outbound layer: a fixed editorially-curated bookmark list."""
    ks = _load()
    srcs = ks["research_sources"]
    assert 6 <= len(srcs) <= 10, "curated list stays a small fixed set (~8)"
    urls = set()
    for s in srcs:
        assert {"name", "org", "url", "desc_en", "desc_zh"} <= set(s), s
        assert s["url"].startswith("https://"), s["url"]
        assert s["url"] not in urls, "duplicate bookmark"
        urls.add(s["url"])
        for k in ("name", "org", "desc_en", "desc_zh"):
            assert isinstance(s[k], str) and s[k].strip(), (s.get("name"), k)
    assert "editorial" in ks["methodology"].lower(), "curation must be disclosed"


def test_knowledge_shelf_no_third_party_content_or_blocked_hosts() -> None:
    """Anti-appropriation guard: the panel is a catalog, not a copy.

    The shelf is the xiaoyinsi 'bookshelf' equivalent done without content
    theft: own MIT docs are cataloged (teaser only), third parties are
    link-outs only, and the blocked host must never appear anywhere in the
    payload (no requests to it, no references to it).
    """
    raw = (DATA / "knowledge_shelf.json").read_text(encoding="utf-8")
    assert "xiaoyinsi" not in raw.lower(), "blocked host must not appear in the panel"
    assert "display-only" in _load()["methodology"].lower()


# --- exporter pure helpers (hermetic fixtures) --------------------------------


def test_ks_classify_fixed_rails() -> None:
    assert et._ks_classify("docs/phase-b-preregistration.md") == "preregistration"
    assert et._ks_classify("docs/track-llm-preregistration.md") == "preregistration"
    assert et._ks_classify("decisions/ADR-006-no-disposable-artifacts-registry.md") == "adr"
    assert et._ks_classify("decisions/index.md") == "adr"  # the ADR registry page
    assert et._ks_classify("docs/RESULTS.md") == "results"
    assert et._ks_classify("docs/track-b-results.md") == "results"
    assert et._ks_classify("docs/data-intake-rubric.md") == "rubric"
    assert et._ks_classify("docs/data-license-allowlist.md") == "rubric"
    assert et._ks_classify("docs/00-vision.md") == "theory"
    assert et._ks_classify("docs/theory-of-computable-reality.md") == "theory"


def test_ks_title_first_heading_or_stem() -> None:
    assert et._ks_title("# Hello **World**\nbody\n", "docs/a.md") == "Hello World"
    assert et._ks_title("no heading here\n", "docs/some-doc.md") == "some-doc"


def test_ks_summary_mines_prose_and_skips_noise() -> None:
    doc = (
        "# Title line\n"
        "<!-- hidden comment -->\n"
        "> 状态：**v0.1 · 2026-08-23**。这是第一句。\n"
        "> 这是第二句，仍然在引言里。\n"
        "```\nprint('fenced code must not leak')\n```\n"
        "| col | col |\n|-----|-----|\n| tbl | row |\n"
        "- **date:** 2026-08-23\n"
        "- **status:** accepted\n"
        "\n"
        "正文第一句。正文第二句！正文第三句？正文第四句不应入选。\n"
    )
    teaser = et._ks_summary(doc)
    assert "这是第一句" in teaser and "这是第二句" in teaser
    assert "fenced code" not in teaser
    assert "col" not in teaser and "tbl" not in teaser
    assert "date:" not in teaser and "accepted" not in teaser
    assert "第四句" not in teaser, "sentence cap (3) must hold"
    assert len(teaser) <= _MAX_TEASER


def test_ks_summary_hard_truncates_overlong_first_sentence() -> None:
    doc = "# T\n" + ("长句" * 300) + "。\n"
    teaser = et._ks_summary(doc)
    assert len(teaser) <= _MAX_TEASER
    assert teaser.endswith("…")


def test_ks_summary_ascii_period_only_on_boundary() -> None:
    doc = "# T\nVersion v0.1.2 shipped today. Second sentence here. Third one. Fourth one.\n"
    teaser = et._ks_summary(doc)
    assert teaser.startswith("Version v0.1.2 shipped today.")
    assert "Second sentence here." in teaser
    assert "Third one." in teaser
    assert "Fourth one." not in teaser, "3-sentence cap"


def test_ks_git_date_outside_repo(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)  # no git repo here
    (tmp_path / "a.md").write_text("# A\n", encoding="utf-8")
    assert et._ks_git_date("a.md") is None  # honest null, never mtime


def test_export_knowledge_shelf_end_to_end(tmp_path, monkeypatch) -> None:
    """Smoke: export over a fixture tree writes a self-consistent catalog."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "decisions").mkdir()
    (tmp_path / "docs" / "phase-x-preregistration.md").write_text(
        "# Phase X 预注册\n\n> 状态：v0.1。第一句。\n\n正文第一句。正文第二句！\n",
        encoding="utf-8",
    )
    (tmp_path / "decisions" / "ADR-042-example.md").write_text(
        "# ADR-042 — Example\n\n- **date:** 2026-08-23\n- **status:** accepted\n\n"
        "## Background\nThere is a temptation. It must be resisted.\n",
        encoding="utf-8",
    )
    web = tmp_path / "web"
    web.mkdir()
    monkeypatch.setattr(et, "WEB", web)
    monkeypatch.chdir(tmp_path)
    et.export_knowledge_shelf()
    payload = json.loads((web / "knowledge_shelf.json").read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["n_docs"] == 2
    assert payload["categories"]["preregistration"] == 1
    assert payload["categories"]["adr"] == 1
    # Outside a git repo the dates are honest nulls (never fabricated).
    assert all(d["date"] is None for d in payload["docs"])
    assert payload["as_of"] is None
    assert payload["snapshot_ts"]
    # No reports/evidence/ in the fixture tree -> the artifact layer must
    # degrade honestly (null sha256/n_bytes), never fabricate a hash.
    assert len(payload["evidence_artifacts"]) == 2
    assert {a["id"] for a in payload["evidence_artifacts"]} == ARTIFACT_IDS
    for a in payload["evidence_artifacts"]:
        assert a["sha256"] is None and a["n_bytes"] is None, a["id"]
    assert "layer 3" in payload["methodology"].lower()
    for d in payload["docs"]:
        assert d["url"].startswith("https://github.com/Rethymus/Aionis/blob/main/")
        assert 0 < len(d["summary"]) <= _MAX_TEASER


def test_export_knowledge_shelf_raises_when_docs_absent(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        et.export_knowledge_shelf()  # _safe_export convention: skip + retain


# --- Layer 3: generated evidence artifacts (sha256 verification loop) ---------


def test_knowledge_shelf_evidence_artifacts_reconcile_to_repo() -> None:
    """Exactly the two round artifacts; sha256/bytes re-computed from the repo.

    This is the reader-side verification loop, enforced at contract level:
    the catalog's sha256 and byte count must equal a fresh re-hash/re-count
    of the tracked file — otherwise a stale catalog would silently mis-verify.
    """
    ks = _load()
    arts = ks["evidence_artifacts"]
    assert isinstance(arts, list) and len(arts) == 2, "exactly two evidence artifacts"
    assert {a["id"] for a in arts} == ARTIFACT_IDS, "artifact ids are pinned"
    for a in arts:
        assert a["path"].startswith("reports/evidence/"), a["id"]
        assert a["url"] == _GITHUB + a["path"], a["id"]
        for k in ("name_en", "name_zh", "desc_en", "desc_zh"):
            assert isinstance(a[k], str) and a[k].strip(), (a["id"], k)
        # Bilingual strings are distinct static content, not translations
        # collapsed onto one value.
        assert a["name_en"] != a["name_zh"], a["id"]
        assert a["desc_en"] != a["desc_zh"], a["id"]
        p = Path(a["path"])
        assert p.is_file(), f"{a['id']} missing from repo — re-export or restore"
        # LF-normalized recompute: the catalog pins the git-blob / GitHub-raw
        # form, so verification must not depend on the checkout's autocrlf.
        raw = p.read_bytes().replace(b"\r\n", b"\n")
        assert a["n_bytes"] == len(raw), f"{a['id']} byte count stale — re-export"
        assert a["sha256"] == hashlib.sha256(raw).hexdigest(), (
            f"{a['id']} sha256 stale — re-export"
        )
    assert "layer 3" in ks["methodology"].lower(), "evidence layer must be disclosed"


def test_knowledge_shelf_artifacts_barrel_and_dict_registered() -> None:
    """Barrel type + /shelf view + dict keys (both locales, non-empty)."""
    barrel = Path("web/src/data/aionis/index.ts").read_text(encoding="utf-8")
    assert "KnowledgeShelfArtifact" in barrel, "barrel type missing"
    assert "evidence_artifacts: KnowledgeShelfArtifact[]" in barrel
    view = Path("web/src/components/shelf/shelf-view.tsx").read_text(encoding="utf-8")
    assert "evidence_artifacts" in view, "/shelf view must render the layer"
    assert "shelf.artifacts.title" in view
    raw = _DICT.read_text(encoding="utf-8")
    zh = raw[raw.index("  zh: {") : raw.index("  en: {")]
    en = raw[raw.index("  en: {") :]
    for key in ("shelf.artifacts.title", "shelf.artifacts.note", "shelf.artifacts.sha"):
        for block in (zh, en):
            m = re.search(rf'"{re.escape(key)}":\s*"([^"]*)"', block)
            assert m, f"dict key {key!r} missing in one locale"
            assert m.group(1).strip(), f"dict key {key!r} empty in one locale"
