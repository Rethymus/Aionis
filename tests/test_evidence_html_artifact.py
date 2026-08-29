"""Contract tests for the standalone evidence HTML artifact (TASK-DISP-G2).

Two layers, both hermetic (no network, no runs/, zero skips):

1. Synthetic-fixture tests of the pure renderer (fixtures constructed in-test
   and clearly labeled as such — the repo bans synthetic data in the RESEARCH
   pipeline, not in labeled unit-test fixtures). They pin: claim numbers
   embedded verbatim, inline SVG present, verdict string present, no leakage
   tokens (undefined / NaN / [object Object] / wall-clock ``now``), zero
   external resources, pinned sort orders, byte determinism, and honest
   degradation when a panel is missing.

2. The committed real artifact (reports/evidence/atlas-claim-v1.html) must
   carry the metrics.json numbers verbatim (combined_ic / CI / p / n_months /
   verdict / config_sig_short), mention SESOI, be fully self-contained (no
   http://, https://, src=), and equal a fresh in-memory render of the current
   panels (the byte-stable contract of the task spec).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import export_evidence_html as ex  # noqa: E402

DATA = Path("web/src/data/aionis")
ARTIFACT = Path("reports/evidence/atlas-claim-v1.html")

LEAK_TOKENS = (
    "undefined",
    "NaN",
    "[object Object]",
    "now(",
    "Date.now",
    "datetime.now",
    "time.time",
)
EXTERNAL_TOKENS = (
    "http://",
    "https://",
    "src=",
    "<script",
    "<link",
    "<iframe",
    "@import",
    "url(",
)


def _fixture_panel() -> dict:
    """Synthetic labeled fixture — NOT research data (unit-test fixture only)."""
    return {
        "metrics": {
            # 0.0127: chosen so no other fixture value contains it as a substring
            "combined_ic": 0.0127,
            "p": 0.032,
            "n_months": 7,
            "ci_lo": 0.0011,
            "ci_hi": 0.0234,
            "verdict": "POSITIVE",
            "jt_look1": "NOT_EQUIVALENT",
            "h6": "PASS",
            "sesoi": 0.01,
            "latest_month": "2026-08-03",
            "n_picks_total": 0,
            "ledger_row": 99,
            "config_sig_short": "deadbeef",
            "snapshot_ts": "2026-08-22T13:32:20.445645+00:00",
        },
        # deliberately NOT month-sorted: renderer must pin the order itself
        "ic_monthly": [
            {"month": "2026-02", "us": None, "cn": 0.03, "combined": -0.04},
            {"month": "2025-12", "us": 0.11, "cn": -0.05, "combined": 0.02},
            {"month": "2026-01", "us": 0.0, "cn": 0.0, "combined": 0.005},
        ],
        "evidence": [
            {
                "n": 2,
                "result": "Phase C differential",
                "estimate": 0.004,
                "ci_lo": -0.01,
                "ci_hi": 0.02,
                "p": 0.5,
                "n_months": 7,
                "grade": "CV-proxy",
            },
            {
                "n": 1,
                "result": "no-CI estimate",
                "estimate": 0.009,
                "ci_lo": None,
                "ci_hi": None,
                "p": None,
                "n_months": 7,
                "grade": "explor.",
            },
        ],
        "provenance": {
            "status": "ok",
            "ledger_row": 99,
            "phase": "fixture",
            "config_sig_short": "deadbeef",
            "config_sig_source": "fixture.build()",
            "result_ts": "2026-08-05T10:27:13.421731+00:00",
            "result_event": "confirmatory:first",
            "freeze": {
                "ledger_row": 98,
                "ts": "2026-08-05T04:19:50.785179+00:00",
                "event": "config_committed",
                "config_sig_short": "deadbeef",
            },
            "contract": {
                "freeze_before_result": True,
                "note": "freeze sha256 == result sha256",
            },
            "headline": {
                "combined_ic": 0.0123456789,
                "p_hac": 0.0321123,
                "ci_lo": 0.0011,
                "ci_hi": 0.0234,
                "n_months": 7.0,
            },
            "snapshot_ts": "2026-08-28T05:51:27.445235+00:00",
        },
    }


# --- layer 1: synthetic fixtures of the pure renderer -------------------------


def test_fixture_embeds_claim_numbers_verbatim() -> None:
    html_out = ex.render_html(_fixture_panel())
    m = _fixture_panel()["metrics"]
    assert m is not None
    for key in ("combined_ic", "ci_lo", "ci_hi", "p", "sesoi", "n_months",
                "ledger_row"):
        assert ex.plain(m[key]) in html_out, f"missing verbatim number: {key}"
    assert m["verdict"] in html_out
    assert m["config_sig_short"] in html_out
    # both headline-card CIs appear as a bracketed pair
    assert f"[{ex.plain(m['ci_lo'])}, {ex.plain(m['ci_hi'])}]" in html_out


def test_fixture_contains_svgs_table_and_provenance() -> None:
    html_out = ex.render_html(_fixture_panel())
    assert html_out.count("<svg") == 2, "forest + monthly-bars SVGs expected"
    assert "<table" in html_out, "data-table fallback expected"
    assert "SESOI" in html_out
    assert "byte-stable artifact" in html_out
    assert ex.GENERATOR_VERSION in html_out
    # the no-CI evidence row must be honestly excluded from the forest itself,
    # but surfaced via an explicit note (nothing silently dropped)
    text = re.sub(r"<[^>]+>", "", html_out)
    assert "#1 no-CI estimate" not in text, "no-CI row must not join the forest"
    assert "无 CI 入账" in text, "exclusion must be noted, not silent"


def test_fixture_no_leakage_tokens() -> None:
    html_out = ex.render_html(_fixture_panel())
    for tok in LEAK_TOKENS:
        assert tok not in html_out, f"leakage/undefined token in artifact: {tok}"


def test_fixture_self_contained() -> None:
    html_out = ex.render_html(_fixture_panel())
    for tok in EXTERNAL_TOKENS:
        assert tok not in html_out, f"external resource reference: {tok}"


def test_fixture_pinned_sort_and_byte_determinism() -> None:
    panel = _fixture_panel()
    once = ex.render_html(panel)
    assert once == ex.render_html(panel), "render must be deterministic"
    shuffled = _fixture_panel()
    assert panel["ic_monthly"] is not None and panel["evidence"] is not None
    shuffled["ic_monthly"] = list(reversed(panel["ic_monthly"]))
    shuffled["evidence"] = list(reversed(panel["evidence"]))
    assert ex.render_html(shuffled) == once, "sort orders must be pinned in code"
    months = re.findall(r"<tr><td>(\d{4}-\d{2})</td>", once)
    assert months == ["2025-12", "2026-01", "2026-02"], months


def test_fixture_missing_panels_degrade_honestly() -> None:
    no_metrics = _fixture_panel()
    no_metrics["metrics"] = None
    out = ex.render_html(no_metrics)
    assert ex.plain(_fixture_panel()["metrics"]["combined_ic"]) not in out, (
        "must not fabricate headline numbers"
    )
    assert "combined_ic · 月度 rank-IC 差分</dt>" not in out, (
        "headline card must be replaced by the notice"
    )
    assert "panel unavailable" in out and "metrics.json" in out

    no_ic = _fixture_panel()
    no_ic["ic_monthly"] = None
    out2 = ex.render_html(no_ic)
    assert "panel unavailable" in out2 and "ic_monthly.json" in out2
    assert "<table" not in out2, "table fallback must degrade away with the panel"
    assert "逐月 combined IC 序列条形图" not in out2, "bars svg must degrade away"
    # forest may legitimately persist (evidence panel still present)
    assert out2.count("panel unavailable") == 2  # bars section + table section

    bare = {"metrics": None, "ic_monthly": None, "evidence": None,
            "provenance": None}
    out3 = ex.render_html(bare)
    for tok in LEAK_TOKENS + EXTERNAL_TOKENS:
        assert tok not in out3
    # headline + forest + bars + table + 2 provenance notices = 6 honest degradations
    assert out3.count("panel unavailable") == 6


# --- layer 2: the committed real artifact ------------------------------------


def _committed() -> str:
    assert ARTIFACT.exists(), (
        "reports/evidence/atlas-claim-v1.html must be generated and committed; "
        "run `uv run python scripts/export_evidence_html.py`"
    )
    # LF-normalized: the generator writes LF, but a git checkout under
    # autocrlf materializes CRLF on disk — compare canonical forms.
    return ARTIFACT.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_real_artifact_matches_metrics_json_verbatim() -> None:
    html_out = _committed()
    m = json.loads((DATA / "metrics.json").read_text(encoding="utf-8"))
    for key in ("combined_ic", "ci_lo", "ci_hi", "p", "n_months", "ledger_row"):
        assert ex.plain(m[key]) in html_out, f"artifact lost panel value: {key}"
    assert m["verdict"] in html_out
    assert m["config_sig_short"] in html_out
    assert f"[{ex.plain(m['ci_lo'])}, {ex.plain(m['ci_hi'])}]" in html_out
    assert "SESOI" in html_out
    # provenance ledger chain from headline_provenance.json (embedded verbatim)
    prov = json.loads((DATA / "headline_provenance.json").read_text(encoding="utf-8"))
    assert prov["freeze"]["ts"] in html_out
    assert prov["result_ts"] in html_out
    assert prov["config_sig_source"] in html_out


def test_real_artifact_self_contained_and_byte_clean() -> None:
    html_out = _committed()
    for tok in EXTERNAL_TOKENS:
        assert tok not in html_out, f"external resource reference: {tok}"
    for tok in LEAK_TOKENS:
        assert tok not in html_out, f"leakage/undefined token: {tok}"
    assert "\r" not in html_out, "artifact must use LF newlines"
    assert html_out.startswith("<!DOCTYPE html>")
    assert "byte-stable artifact" in html_out


def test_real_artifact_equals_fresh_render_of_current_panels() -> None:
    """Byte-stable contract: committed artifact == fresh render (no drift)."""
    fresh = ex.render_html(ex.load_panel(ex.PANEL_DIR))
    assert _committed() == fresh
