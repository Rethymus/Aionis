"""Contract tests for the provenance-chained research dossier (TASK-DSP-D1).

Two layers, both hermetic (no network, no writes, zero skips):

1. Synthetic-fixture tests of the pipeline (fixtures constructed in-test and
   clearly labeled as such — the repo bans synthetic data in the RESEARCH
   pipeline, not in labeled unit-test fixtures). They pin: end-to-end
   assembly+render, S-registry integrity shas, latest-ledger-row selection,
   the [S#] citation-closure hard gate (orphan citation / uncited source /
   number-without-citation all raise), byte determinism with pinned sort
   orders, self-containment with scheme-stripped external locators, and honest
   degradation when a source is missing.

2. The committed real artifact (reports/evidence/research-dossier-v1.html):
   byte-equal to a fresh render of the real assembly, verbatim reconciliation
   against metrics.json, zero external resources, S-registry integrity shas
   recomputed against the actual files / ledger lines, latest horizon-row
   selection re-derived independently, and the citation closure re-checked.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import export_research_dossier as dr  # noqa: E402

DATA = Path("web/src/data/aionis")
LEDGER = Path("runs/ledger.jsonl")
ARTIFACT = Path("reports/evidence/research-dossier-v1.html")

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
SECTIONS = (
    "1 · 执行摘要",
    "2 · 研究设计与门禁",
    "3 · 数据来源与可溯源性",
    "4 · 建模与分析",
    "5 · 证据与文献语境",
    "6 · 局限与边界",
    "7 · 引用完整性自检",
)


# --- synthetic fixtures (labeled unit-test fixtures, NOT research data) -------


def _canon(obj: object) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")


def _fixture_horizon_results() -> dict:
    def cell(mean_diff: float, lo: float, hi: float, holds: bool) -> dict:
        return {
            "arm_enhanced": "arm_x",
            "enhanced_mean_ic": 0.01,
            "base_mean_ic": 0.009,
            "n_months": 12,
            "mean_diff": mean_diff,
            "se_hac": 0.005,
            "ci_half": 0.01,
            "ci_lo": lo,
            "ci_hi": hi,
            "dm_stat": 0.1,
            "dm_p_mbb": 0.9,
            "dm_flag": "ok",
            "publishable_ci_half": True,
            "null_holds": holds,
        }

    return {
        "10": {
            "B": cell(0.0001, -0.02, 0.02, True),
            "C": cell(-0.0002, -0.03, 0.03, True),
            "D": cell(0.0003, -0.025, 0.025, True),
            "E1": cell(-0.0004, -0.015, 0.015, True),
        },
        "42": {
            "B": cell(-0.0011, -0.026, 0.024, True),
            "C": cell(0.0012, -0.031, 0.029, True),
            "D": cell(-0.0013, -0.027, 0.023, True),
            "E1": cell(0.0014, -0.018, 0.014, True),
        },
    }


def _fixture_payloads() -> dict[str, tuple[object, str]]:
    """Synthetic labeled fixture — NOT research data (unit-test fixture only)."""
    metrics = {
        "combined_ic": 0.0123,
        "p": 0.321,
        "n_months": 12,
        "ci_lo": -0.011,
        "ci_hi": 0.034,
        "verdict": "NULL",
        "jt_look1": "NOT_EQUIVALENT",
        "h6": "PASS",
        "sesoi": 0.01,
        "latest_month": "2026-08-03",
        "n_picks_total": 0,
        "ledger_row": 4,
        "config_sig_short": "cafe1234",
        "snapshot_ts": "2026-08-22T13:32:20.445645+00:00",
    }
    # deliberately NOT month-sorted: the renderer must pin the order itself
    ic_monthly = [
        {"month": "2026-02", "us": None, "cn": 0.03, "combined": -0.04},
        {"month": "2025-12", "us": 0.11, "cn": -0.05, "combined": 0.02},
        {"month": "2026-01", "us": 0.0, "cn": 0.0, "combined": 0.005},
    ]
    calibration = {
        "method": "platt",
        "walk_forward": True,
        "min_train_months": 12,
        "regions": {
            "us": {"n_months": 2, "pooled_ece": 0.11, "series": []},
            "cn": {"n_months": 2, "pooled_ece": 0.22, "series": []},
        },
    }
    score_diagnostics = [
        {"month": "2026-02", "region": "us", "n": 12, "rank_autocorr": None},
        {"month": "2026-01", "region": "cn", "n": 12, "rank_autocorr": 0.42},
        {"month": "2026-01", "region": "us", "n": 12, "rank_autocorr": 0.91},
    ]
    data_health = {
        "status": "ok",
        "summary": {"n_panels": 3, "n_frozen": 1, "n_daily": 1, "n_cadence": 1},
        "panels": [
            {"key": "a", "category": "frozen", "as_of": "2026-08-03"},
            {"key": "b", "category": "daily", "as_of": "2026-08-28"},
            {"key": "c", "category": "cadence", "as_of": None},
        ],
    }
    # a raw https string inside the catalog must never leak into the artifact
    api_catalog = {
        "status": "ok",
        "endpoints": [
            {"status": "available", "freshness": "frozen",
             "license": "Lic A", "as_of": "2026-08-03",
             "source": "internal-only https://secret.example/x"},
            {"status": "available", "freshness": "daily",
             "license": "Lic A", "as_of": "2026-08-28", "source": "s2"},
            {"status": "available", "freshness": "cadence",
             "license": "Lic B", "as_of": None, "source": "s3"},
        ],
    }
    evidence = [
        {"n": 2, "result": "Phase C differential", "estimate": 0.004,
         "ci_lo": -0.01, "ci_hi": 0.02, "p": 0.5, "n_months": 12,
         "grade": "CV-proxy"},
        {"n": 1, "result": "no-CI estimate", "estimate": 0.009,
         "ci_lo": None, "ci_hi": None, "p": None, "n_months": 12,
         "grade": "explor."},
    ]
    provenance = {
        "status": "ok",
        "ledger_row": 4,
        "phase": "fixture_track",
        "config_sig_short": "cafe1234",
        "config_sig_source": "fixture.build() (#1 cumulative)",
        "result_ts": "2026-04-01T00:00:00+00:00",
        "result_event": "confirmatory:first",
        "freeze": {
            "ledger_row": 1,
            "ts": "2026-01-01T00:00:00+00:00",
            "event": "config_committed",
            "config_sig_short": "cafe1234",
        },
        "headline": {"combined_ic": 0.0123},
        "contract": {"freeze_before_result": True, "note": "fixture contract"},
        "snapshot_ts": "2026-08-28T05:51:27.445235+00:00",
    }
    knowledge_shelf = {
        "research_sources": [
            {"name": "Fixture Shelf A", "org": "Org A",
             "url": "https://example.org/shelf-a",
             "desc_zh": "合成夹具书签 A(仅测试)"},
            {"name": "Fixture Shelf B", "org": "Org B",
             "url": "http://example.org/shelf-b",
             "desc_zh": "合成夹具书签 B(仅测试)"},
        ],
    }
    objs = {
        "metrics": metrics,
        "ic_monthly": ic_monthly,
        "calibration": calibration,
        "score_diagnostics": score_diagnostics,
        "data_health": data_health,
        "api_catalog": api_catalog,
        "evidence": evidence,
        "provenance": provenance,
        "knowledge_shelf": knowledge_shelf,
    }
    payloads = {k: (v, hashlib.sha256(_canon(v)).hexdigest())
                for k, v in objs.items()}
    payloads["artifact_atlas"] = (
        None, hashlib.sha256(b"fixture-atlas-bytes").hexdigest()
    )
    payloads["doc_phase_d"] = (
        None, hashlib.sha256(b"fixture-doc-phase-d").hexdigest()
    )
    payloads["doc_track_c"] = (
        None, hashlib.sha256(b"fixture-doc-track-c").hexdigest()
    )
    payloads["doc_rubric"] = (
        None, hashlib.sha256(b"fixture-doc-rubric").hexdigest()
    )
    return payloads


def _fixture_ledger_lines() -> list[str]:
    """Shuffled-order ledger: an OLDER horizon row (line 2) before the newest
    (line 3) — the assembler must pick the newest (last match)."""
    r1 = {"ts": "2026-01-01T00:00:00+00:00", "event": "config_committed",
          "phase": "fixture_track", "config_sig_short": "cafe1234"}
    r2 = {"ts": "2026-02-01T00:00:00+00:00", "event": "exploratory",
          "phase": "sensitivity_horizon", "horizons": [10],
          "frozen_confirmatory_horizon": 21,
          "results": {}, "null_criterion": "older sweep (must NOT be picked)",
          "notes": "older"}
    r3 = {"ts": "2026-03-01T00:00:00+00:00", "event": "exploratory",
          "phase": "sensitivity_horizon", "horizons": [10, 42],
          "frozen_confirmatory_horizon": 21,
          "results": _fixture_horizon_results(),
          "null_criterion": "null_holds iff the differential's 95% HAC CI "
                            "brackets zero",
          "notes": "newest sweep"}
    r4 = {"ts": "2026-04-01T00:00:00+00:00", "event": "confirmatory:first",
          "phase": "fixture_track", "combined_ic": {"mean": 0.0123}}
    return [json.dumps(r, ensure_ascii=False) for r in (r1, r2, r3, r4)]


def _fixture_assembly() -> dr.Assembly:
    return dr.build_assembly(_fixture_payloads(), _fixture_ledger_lines())


# --- layer 1a: pipeline mechanics on synthetic fixtures -----------------------


def test_fixture_pipeline_end_to_end() -> None:
    a = _fixture_assembly()
    html_out = dr.render(a)
    assert html_out.startswith("<!DOCTYPE html>")
    for sec in SECTIONS:
        assert sec in html_out, f"missing section: {sec}"
    assert dr.ARTIFACT_ID in html_out
    assert dr.DOSSIER_VERSION in html_out
    assert "<!-- s-registry -->" in html_out and "<!-- /s-registry -->" in html_out
    assert html_out.count("<svg") == 2, "forest + monthly-bars SVGs expected"
    assert "<table" in html_out
    # Round-34: bookmarks come from the shared ks_sources.RESEARCH_SOURCES
    # literals (8 entries), and the knowledge_shelf generated panel is no
    # longer a hashed source (it embeds this dossier's own hash — circular).
    # Composition: 8 panels + 2 ledger rows + 3 docs + 1 artifact + HLZ + 8
    # bookmarks = 23.
    assert len(a.sources) == 23
    assert len({s.sid for s in a.sources}) == 23
    # The generated shelf payload, if present in inputs, must be IGNORED
    # (no hashed entry for it — the circular-hash break).
    assert not any(
        s.type == "panel" and "knowledge_shelf" in s.locator for s in a.sources
    ), "knowledge_shelf.json must not re-enter the registry (circular hash)"


def test_fixture_registry_integrity_and_latest_row_selection() -> None:
    a = _fixture_assembly()
    # panel integrity = sha256 of the fixture bytes (hex present in the entry)
    for s in a.sources:
        if s.type != "panel":
            continue
        key = next(k for k, v in a.sid.items() if v == s.sid)
        want = _fixture_payloads()[key][1]
        assert f"sha256:{want}" in s.integrity, key
    # ledger horizon = the NEWEST exploratory row (line 3), not line 2
    assert a.ledger_horizon is not None and a.ledger_horizon.lineno == 3
    assert a.ledger_horizon.rec["ts"] == "2026-03-01T00:00:00+00:00"
    assert a.ledger_horizon.sha == hashlib.sha256(
        _fixture_ledger_lines()[2].encode("utf-8")
    ).hexdigest()
    # freeze row located at line 1 (matches provenance.freeze ts/row)
    assert a.ledger_freeze is not None and a.ledger_freeze.lineno == 1
    assert a.ledger_freeze.sha == hashlib.sha256(
        _fixture_ledger_lines()[0].encode("utf-8")
    ).hexdigest()


def test_fixture_closure_orphan_citation_raises() -> None:
    a = _fixture_assembly()
    html_out = dr.render(a)
    tampered = html_out.replace("</body>", " [S99]</body>")
    with pytest.raises(dr.CitationClosureError):
        dr.check_citation_closure(tampered, a.sources)


def test_fixture_closure_uncited_source_raises() -> None:
    a = _fixture_assembly()
    html_out = dr.render(a)
    hlz_sid = a.sid["ext_hlz"]
    needle = f'<span class="cite">[{hlz_sid}]</span>'
    assert html_out.count(needle) == 1, "fixture HLZ chip must appear once"
    tampered = html_out.replace(needle, "")
    with pytest.raises(dr.CitationClosureError):
        dr.check_citation_closure(tampered, a.sources)


def test_fixture_closure_uncited_number_raises() -> None:
    a = _fixture_assembly()
    html_out = dr.render(a)
    tampered = html_out.replace(
        "</body>", '<p class="na">stray 0.4321 without citation</p></body>'
    )
    with pytest.raises(dr.CitationClosureError):
        dr.check_citation_closure(tampered, a.sources)


def test_fixture_byte_determinism_and_pinned_sorts() -> None:
    a = _fixture_assembly()
    once = dr.render(a)
    assert once == dr.render(a), "render must be deterministic"
    # reversed list payloads must not change a single byte (sorts pinned;
    # research_sources is deliberately excluded — its order is editorial and
    # pinned as committed in the panel)
    payloads = _fixture_payloads()
    for key in ("ic_monthly", "evidence", "score_diagnostics"):
        obj, sha = payloads[key]
        assert isinstance(obj, list)
        payloads[key] = (list(reversed(obj)), sha)
    shuffled_html = dr.render(dr.build_assembly(payloads, _fixture_ledger_lines()))
    assert shuffled_html == once, "list order must not affect output bytes"


def test_fixture_self_contained_and_defanged_locators() -> None:
    html_out = dr.render(_fixture_assembly())
    for tok in EXTERNAL_TOKENS:
        assert tok not in html_out, f"external resource reference: {tok}"
    # bookmark locators render scheme-stripped: the real shared bookmarks
    # (ks_sources.RESEARCH_SOURCES) must appear WITHOUT their https:// scheme,
    # and the fixture's shelf payload (now ignored) must never leak either.
    assert "www.bis.org" in html_out
    assert "https://www.bis.org" not in html_out
    assert "example.org/shelf-a" not in html_out
    assert "example.org/shelf-b" not in html_out
    assert "secret.example" not in html_out
    for tok in LEAK_TOKENS:
        assert tok not in html_out, f"leakage/undefined token: {tok}"


def test_fixture_embeds_fixture_numbers_verbatim() -> None:
    a = _fixture_assembly()
    html_out = dr.render(a)
    m = _fixture_payloads()["metrics"][0]
    assert isinstance(m, dict)
    for key in ("combined_ic", "ci_lo", "ci_hi", "p", "n_months", "ledger_row"):
        assert dr.plain(m[key]) in html_out, f"missing verbatim number: {key}"
    assert f"[{dr.plain(m['ci_lo'])}, {dr.plain(m['ci_hi'])}]" in html_out
    assert m["verdict"] in html_out and m["config_sig_short"] in html_out
    # horizon table: all 8 cells hold, so all marks read 成立
    assert html_out.count("holds-true") >= 8


def test_fixture_missing_sources_degrade_honestly() -> None:
    # Round-34: knowledge_shelf is no longer an input (bookmarks come from the
    # shared ks_sources literals), so honest degradation is exercised on a
    # panel that IS still an input: drop calibration and the calibration
    # section must degrade to its NA marker without breaking the closure.
    payloads = _fixture_payloads()
    del payloads["calibration"]
    a = dr.build_assembly(payloads, _fixture_ledger_lines())
    out = dr.render(a)  # closure still holds (fewer sources, still all cited)
    assert "source unavailable" in out
    assert not any(s.locator.endswith("calibration_reliability.json") for s in a.sources)

    a2 = dr.build_assembly(_fixture_payloads(), None)
    out2 = dr.render(a2)
    assert "source unavailable" in out2
    assert "ledger_horizon" not in a2.sid and "ledger_freeze" not in a2.sid
    assert "horizon 稳健性" in out2  # section exists, degrades inside

    # provenance removed -> freeze row not located; render still clean
    payloads3 = _fixture_payloads()
    del payloads3["provenance"]
    a3 = dr.build_assembly(payloads3, _fixture_ledger_lines())
    out3 = dr.render(a3)
    assert "ledger_freeze" not in a3.sid
    assert "source unavailable" in out3


# --- layer 2: the committed real artifact -------------------------------------


def _committed() -> str:
    assert ARTIFACT.exists(), (
        "reports/evidence/research-dossier-v1.html must be generated and "
        "committed; run `uv run python scripts/export_research_dossier.py`"
    )
    # LF-normalized: the generator writes LF, but a git checkout under
    # autocrlf materializes CRLF on disk — compare canonical forms.
    return ARTIFACT.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_real_artifact_equals_fresh_render() -> None:
    """Byte-stable contract: committed artifact == fresh render (no drift)."""
    fresh = dr.render(dr.assemble())
    assert _committed() == fresh


def test_real_artifact_metrics_json_verbatim_reconciliation() -> None:
    html_out = _committed()
    m = json.loads((DATA / "metrics.json").read_text(encoding="utf-8"))
    for key in ("combined_ic", "ci_lo", "ci_hi", "p", "n_months", "sesoi",
                "ledger_row", "n_picks_total"):
        assert dr.plain(m[key]) in html_out, f"artifact lost panel value: {key}"
    for key in ("verdict", "config_sig_short", "jt_look1", "h6", "latest_month",
                "snapshot_ts"):
        assert str(m[key]) in html_out, f"artifact lost panel string: {key}"
    assert f"[{dr.plain(m['ci_lo'])}, {dr.plain(m['ci_hi'])}]" in html_out
    prov = json.loads(
        (DATA / "headline_provenance.json").read_text(encoding="utf-8")
    )
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
    assert html_out.endswith("\n") and not html_out.endswith("\n\n")
    assert dr.DOSSIER_VERSION in html_out
    for sec in SECTIONS:
        assert sec in html_out


def test_real_sregistry_integrity_shas_match_files() -> None:
    a = dr.assemble()
    assert len(a.sources) >= 20
    for s in a.sources:
        if s.type == "external":
            assert "self-declared" in s.integrity, (
                "external integrity must be honestly self-declared"
            )
            continue
        hexes = re.findall(r"sha256:([0-9a-f]{64})", s.integrity)
        assert len(hexes) == 1, f"integrity must carry one sha256: {s.sid}"
        want = hexes[0]
        if s.type in ("panel", "doc", "artifact"):
            got = hashlib.sha256(Path(s.locator).read_bytes()).hexdigest()
            assert got == want, f"{s.sid} {s.locator}: registry sha drifted"
        elif s.type == "ledger":
            m = re.search(r"line (\d+)", s.locator)
            assert m is not None
            lineno = int(m.group(1))
            raw = LEDGER.read_text(encoding="utf-8").splitlines()[lineno - 1]
            got = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            assert got == want, f"{s.sid} ledger line {lineno}: sha mismatch"


def test_real_latest_horizon_row_selection_and_crosscheck() -> None:
    a = dr.assemble()
    lines = LEDGER.read_text(encoding="utf-8").splitlines()
    matches = []
    for i, raw in enumerate(lines, 1):
        rec = json.loads(raw)
        if (rec.get("phase") == "sensitivity_horizon"
                and rec.get("event") == "exploratory"):
            matches.append((i, rec.get("ts")))
    assert matches, "ledger must contain sensitivity_horizon exploratory rows"
    newest = max(matches, key=lambda t: t[1])
    assert a.ledger_horizon is not None
    assert a.ledger_horizon.lineno == newest[0]
    # freeze cross-check: provenance.freeze row really is config_committed
    prov = a.payloads["provenance"]
    assert isinstance(prov, dict)
    assert a.ledger_freeze is not None
    assert a.ledger_freeze.lineno == prov["freeze"]["ledger_row"]
    assert a.ledger_freeze.rec["event"] == "config_committed"
    assert a.ledger_freeze.rec["ts"] == prov["freeze"]["ts"]
    # result-row cross-check embedded in the render (freeze -> result chain)
    assert str(prov["freeze"]["ledger_row"]) in _committed()
    assert str(prov["ledger_row"]) in _committed()


def test_real_horizon_row_content_in_artifact() -> None:
    a = dr.assemble()
    assert a.ledger_horizon is not None
    rec = a.ledger_horizon.rec
    html_out = _committed()
    # the freeze-chain paragraph embeds the ledger stamps verbatim
    assert rec["ts"] in html_out
    assert "frozen_confirmatory_horizon=" + dr.plain(
        rec["frozen_confirmatory_horizon"]
    ) in html_out
    assert rec["null_criterion"].replace("'", "&#x27;") in html_out
    # every (horizon, phase) cell must be present and null_holds rendered
    results = rec["results"]
    n_cells = 0
    for h in sorted(results):
        for ph in ("B", "C", "D", "E1"):
            r = results[h][ph]
            n_cells += 1
            assert dr.f4(r["mean_diff"]) in html_out
            assert dr.f4(r["ci_lo"]) in html_out
            assert dr.f4(r["ci_hi"]) in html_out
            assert ("成立" if r["null_holds"] else "不成立") in html_out
    assert n_cells == 8
    # direction colour classes present (blue/gray — never red/green)
    assert "holds-true" in html_out


def test_real_citation_closure_on_committed() -> None:
    a = dr.assemble()
    html_out = _committed()
    ids = {s.sid for s in a.sources}
    cited = set(re.findall(r"\[(S\d+)\]", html_out))
    assert cited <= ids, f"orphan citations: {sorted(cited - ids)}"
    assert ids <= cited, f"uncited sources: {sorted(ids - cited)}"
    # re-run the full hard gate against the committed bytes
    dr.check_citation_closure(html_out, a.sources)
