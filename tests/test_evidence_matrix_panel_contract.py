"""Contract: the web evidence-matrix panel mirror cannot drift from reality.

Round 182 lesson (2026-10-05): ``export_evidence_matrix_manifest`` writes BOTH
``reports/evidence/evidence-matrix-v1.json`` AND the web panel mirror
``web/src/data/aionis/evidence_matrix.json``. A cascade commit that included
only the reports side passed a fully green CI — the mirror kept the superseded
dossier sha256 until caught by accident. This test pins the three-way
consistency that was unguarded:

  1. panel.artifacts == manifest.artifacts (id / sha256 / bytes), and
  2. every artifact sha256 matches the artifact file actually on disk.

Hermetic: reads committed files only. Any re-render of an upstream artifact
(dossier / atlas / shelf) without committing the mirror fails here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "reports/evidence/evidence-matrix-v1.json"
PANEL = ROOT / "web/src/data/aionis/evidence_matrix.json"
ARTIFACT_DIR = ROOT / "reports/evidence"


def test_panel_mirror_matches_committed_manifest() -> None:
    panel = json.loads(PANEL.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert panel["id"] == manifest["id"] == "evidence-matrix-v1"
    assert panel["version"] == manifest["version"], (
        "the mirror and the manifest must advance their version together"
    )
    p_by_id = {a["id"]: a for a in panel["artifacts"]}
    m_by_id = {a["id"]: a for a in manifest["artifacts"]}
    assert p_by_id.keys() == m_by_id.keys(), (
        f"artifact id sets diverged: panel={sorted(p_by_id)} "
        f"manifest={sorted(m_by_id)}"
    )
    for aid, m_art in m_by_id.items():
        p_art = p_by_id[aid]
        assert p_art["sha256"] == m_art["sha256"], (
            f"{aid}: panel sha {p_art['sha256'][:12]} != manifest sha "
            f"{m_art['sha256'][:12]} — the web mirror was not committed "
            f"with the manifest"
        )
        assert p_art["bytes"] == m_art["bytes"], f"{aid}: byte counts diverged"


def test_every_artifact_sha_matches_disk() -> None:
    """Each catalogued sha256 must equal the artifact file on disk.

    This is the drift class that slipped through green CI on 2026-10-05:
    an upstream artifact was re-rendered (dossier) while the committed
    mirror still carried the superseded hash.
    """

    panel = json.loads(PANEL.read_text(encoding="utf-8"))
    for art in panel["artifacts"]:
        f = ROOT / art["path"]
        assert f.exists(), f"{art['id']}: catalogued artifact missing ({art['path']})"
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        assert digest == art["sha256"], (
            f"{art['id']}: catalogued sha {art['sha256'][:12]} != on-disk sha "
            f"{digest[:12]} — the artifact was re-rendered without updating "
            f"the committed mirror"
        )
        assert f.stat().st_size == art["bytes"], f"{art['id']}: byte count stale"
