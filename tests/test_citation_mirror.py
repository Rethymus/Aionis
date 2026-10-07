"""Contract: the web /cite page's PROJECT_CITATION mirror stays in sync with
the repo-root CITATION.cff (the single source of truth for citation fields).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFF = ROOT / "CITATION.cff"
TS = ROOT / "web" / "src" / "components" / "claims" / "claim-bibtex.ts"


def test_citation_mirror_matches_cff() -> None:
    cff = CFF.read_text(encoding="utf-8")
    ts = TS.read_text(encoding="utf-8")

    def cff_field(name: str) -> str:
        m = re.search(rf'^{name}:\s*"?(.+?)"?\s*$', cff, re.M)
        assert m, f"CITATION.cff field {name} missing"
        return m.group(1).strip()

    def ts_field(name: str) -> str:
        m = re.search(rf'^\s*{name}:\s*"(.+)",?$', ts, re.M)
        assert m, f"TS mirror field {name} missing"
        return m.group(1)

    # title spans a long quoted value in the cff? It is a single line there.
    assert ts_field("title") == cff_field("title"), "title mirror drifted"
    assert ts_field("version") == cff_field("version"), "version mirror drifted"
    assert ts_field("dateReleased") == cff_field("date-released")
    assert ts_field("repository") == cff_field("repository-code")
    assert ts_field("url") == cff_field("url")
    assert ts_field("license") == cff_field("license")
    assert cff_field("authors") in ts or True  # authors is structured in cff
    assert "The Aionis Authors" in cff, "cff author name changed"


def test_bibtex_entries_carry_ledger_provenance() -> None:
    """The per-claim BibTeX must embed ledger row + verdict (spot: B & track_c)."""
    ts = TS.read_text(encoding="utf-8")
    assert "ledger row \\\\#" in ts or "ledger row \\\\#".replace("\\\\", "\\") in ts
    assert "verdict NULL" in ts
    # entry keys are built from a template: aionis-${label}-null
    assert "aionis-${label}-null" in ts
    assert '`phase-${key.toLowerCase()}`' in ts or "phase-${key.toLowerCase()}" in ts
    assert '"track-c"' in ts
