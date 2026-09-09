"""Contract tests for the horizon-robustness panel (web/src/data/aionis/).

TASK-H1: the /track calibration tab renders this panel — a READ-ONLY
projection of the LATEST ``event=="exploratory" and phase=="sensitivity_
horizon"`` ledger row (the h=10/h=42 sweep of the frozen h=21 B/C/D/E1
differentials). No research face is touched: the exporter only re-shapes an
existing tracked ledger row into a browser-renderable summary.

Hermetic checks: the synthetic ledger fixtures are built INSIDE these tests
and used only as test fixtures (the one mock-like data the repo rules allow);
they pin latest-row selection, exact field mapping + 6-dp rounding, honest
nulls for missing phases/horizons, and the three-valued robustness aggregate.
The committed panel is reconciled against the TRACKED runs/ledger.jsonl by
regenerating the export in-memory and requiring byte-level payload equality
(modulo the export clock) — a silent ledger edit or exporter drift surfaces
here. Registration in the freshness map / API catalog / web barrel / i18n
dict is asserted on both the code constants and the committed manifests.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

DATA = Path("web/src/data/aionis")
PANEL = DATA / "horizon_robustness.json"
BARREL = DATA / "index.ts"
DICT = Path("web/src/i18n/dict.ts")
sys.path.insert(0, str(Path("scripts").resolve()))
import export_terminal_data as et  # noqa: E402

# --- fixture machinery (labeled synthetic test fixtures) ----------------------

NULL_CRITERION = "null_holds iff the differential's 95% HAC CI brackets zero"

CELL_FIELDS = {
    "enhanced_mean_ic",
    "base_mean_ic",
    "mean_diff",
    "ci_lo",
    "ci_hi",
    "dm_p_mbb",
    "null_holds",
}


def _cell(
    *,
    arm: str = "arm_state",
    enhanced: float = 0.004606742411888962,
    base: float = 0.0037633437097247128,
    diff: float = 0.0008433987021642504,
    ci_lo: float = -0.007753139780905697,
    ci_hi: float = 0.009439937185234198,
    p: float = 0.8555722138930535,
    holds: bool | None = True,
    arm_base: str | None = None,
) -> dict:
    """One (phase, horizon) results cell shaped like the real sweep row."""
    cell = {
        "arm_enhanced": arm,
        "enhanced_mean_ic": enhanced,
        "base_mean_ic": base,
        "n_months": 126,
        "mean_diff": diff,
        "se_hac": 0.004386069616003657,
        "ci_half": 0.008596538483069948,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "dm_stat": -0.15567301792666466,
        "dm_p_mbb": p,
        "dm_flag": "ok",
        "publishable_ci_half": True,
        "null_holds": holds,
    }
    if arm_base is not None:
        cell["arm_base"] = arm_base
    return cell


def _sweep_row(ts: str, results: dict, notes: str = "synthetic fixture row") -> dict:
    return {
        "ts": ts,
        "event": "exploratory",
        "phase": "sensitivity_horizon",
        "horizons": [10, 42],
        "frozen_confirmatory_horizon": 21,
        "results": results,
        "null_criterion": NULL_CRITERION,
        "notes": notes,
    }


def _non_claim_row(ts: str, i: int) -> dict:
    return {"ts": ts, "event": "config_committed", "phase": "B", "config_sig": f"sig{i}"}


def _run_export(tmp_path, monkeypatch, rows: list[dict]) -> dict:
    """Write the synthetic ledger + run the exporter in an isolated cwd/web."""
    runs = tmp_path / "runs"
    runs.mkdir(exist_ok=True)
    (runs / "ledger.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )
    web = tmp_path / "web"
    web.mkdir(exist_ok=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(et, "WEB", web)
    et.export_horizon_robustness()
    return json.loads((web / "horizon_robustness.json").read_text(encoding="utf-8"))


# --- exporter: latest-row selection + exact mapping (synthetic ledger) --------


def test_export_selects_latest_row_and_maps_fields(tmp_path, monkeypatch) -> None:
    """The LAST exploratory sensitivity_horizon row wins; fields map + round."""
    older = _sweep_row(
        "2026-07-29T03:35:22+00:00",
        {"10": {"B": _cell(diff=0.111)}, "42": {"B": _cell(diff=0.222)}},
    )
    newer = _sweep_row(
        "2026-07-30T05:29:47+00:00",
        {
            "10": {
                "B": _cell(arm="arm_state"),
                "C": _cell(arm="arm_macro"),
                "D": _cell(arm="arm_rel"),
                "E1": _cell(arm="arm_prop", arm_base="arm_base_self"),
            },
            "42": {
                "B": _cell(arm="arm_state"),
                "C": _cell(arm="arm_macro"),
                "D": _cell(arm="arm_rel"),
                "E1": _cell(arm="arm_prop", arm_base="arm_base_self"),
            },
        },
    )
    payload = _run_export(
        tmp_path,
        monkeypatch,
        [
            _non_claim_row("2026-07-01T00:00:00+00:00", 1),
            older,
            _non_claim_row("2026-07-02T00:00:00+00:00", 2),
            newer,
        ],
    )
    assert payload["status"] == "ok"
    assert payload["source_ts"] == "2026-07-30T05:29:47+00:00", "latest row, not the older sweep"
    assert payload["frozen_confirmatory_horizon"] == 21
    assert payload["horizons"] == [10, 42]
    assert list(payload["phases"]) == ["B", "C", "D", "E1"], "row's own phase order kept"
    # Exact 6-dp rounding of the raw ledger float (never a display-formatting loss).
    assert payload["phases"]["B"]["h10"]["mean_diff"] == round(0.0008433987021642504, 6)
    assert payload["phases"]["B"]["h10"]["enhanced_mean_ic"] == round(
        0.004606742411888962, 6
    )
    for ph, arm in (("B", "arm_state"), ("C", "arm_macro"), ("D", "arm_rel")):
        entry = payload["phases"][ph]
        assert entry["arm_enhanced"] == arm
        assert "arm_base" not in entry, "shared-base phases carry no per-phase arm_base"
        assert entry["null_holds_both"] is True
        for h in ("h10", "h42"):
            assert set(entry[h]) == CELL_FIELDS, (ph, h)
            assert entry[h]["null_holds"] is True
    e1 = payload["phases"]["E1"]
    assert e1["arm_enhanced"] == "arm_prop"
    assert e1["arm_base"] == "arm_base_self", "E1's beyond-SELF base is preserved"
    assert payload["horizon_robust_all"] is True
    assert payload["null_criterion"] == NULL_CRITERION
    assert payload["notes"] == "synthetic fixture row"
    assert "snapshot_ts" in payload, "terminal panels carry the export stamp"


def test_export_missing_phase_and_horizon_is_honest_null(tmp_path, monkeypatch) -> None:
    """A phase absent from a horizon's bucket -> null cell + null aggregate."""
    row = _sweep_row(
        "2026-07-30T05:29:47+00:00",
        {
            "10": {"B": _cell(), "C": _cell(arm="arm_macro"), "D": _cell(arm="arm_rel")},
            # h42 lost C and D entirely (partial coverage in the row).
            "42": {"B": _cell()},
        },
    )
    payload = _run_export(tmp_path, monkeypatch, [row])
    assert set(payload["phases"]) == {"B", "C", "D"}, "union of the row's own phases"
    assert payload["phases"]["B"]["h42"]["mean_diff"] == round(
        0.0008433987021642504, 6
    )
    for missing in ("C", "D"):
        entry = payload["phases"][missing]
        assert entry["h42"] is None, "missing horizon cell is an honest null"
        assert entry["null_holds_both"] is None, "cannot claim both with one missing"
    assert payload["horizon_robust_all"] is None, "incomplete coverage is not 'all holds'"


def test_export_explicit_false_breaks_the_aggregate(tmp_path, monkeypatch) -> None:
    """A broken null at one horizon is False (not null) and sinks the total."""
    row = _sweep_row(
        "2026-07-30T05:29:47+00:00",
        {
            "10": {"B": _cell(holds=True)},
            "42": {"B": _cell(holds=False)},
        },
    )
    payload = _run_export(tmp_path, monkeypatch, [row])
    b = payload["phases"]["B"]
    assert b["h10"]["null_holds"] is True and b["h42"]["null_holds"] is False
    assert b["null_holds_both"] is False
    assert payload["horizon_robust_all"] is False


def test_export_absent_sweep_row_skips_via_safe_export(
    tmp_path, monkeypatch, capsys
) -> None:
    """No sweep row (or no ledger) -> FileNotFoundError, so _safe_export skips
    and the tracked JSON retains its last committed value. Never fabricated."""
    # (a) ledger present, but no exploratory sensitivity_horizon row in it.
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "ledger.jsonl").write_text(
        json.dumps(_non_claim_row("2026-07-01T00:00:00+00:00", 1)) + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        et.export_horizon_robustness()
    # (b) ledger absent entirely (fresh CI checkout — runs/ is not exported).
    empty = tmp_path / "checkout_without_ledger"
    empty.mkdir()
    monkeypatch.chdir(empty)
    with pytest.raises(FileNotFoundError):
        et.export_horizon_robustness()
    # (c) the _safe_export guard swallows exactly this failure + logs the skip.
    ret = et._safe_export("horizon_robustness", et.export_horizon_robustness)
    assert ret is None
    assert "SKIP horizon_robustness" in capsys.readouterr().out


# --- committed panel (tracked JSON, generated from the REAL tracked ledger) ----


def _load() -> dict:
    return json.loads(PANEL.read_text(encoding="utf-8"))


def test_horizon_robustness_panel_shape_and_pins() -> None:
    """Field contract + measured pins on the committed panel (2026-08-28)."""
    hr = _load()
    assert hr["status"] == "ok"
    assert hr["horizons"] == [10, 42]
    assert hr["frozen_confirmatory_horizon"] == 21
    assert hr["source_ts"] == "2026-07-30T05:29:47+00:00", "the latest sweep row's ts"
    assert list(hr["phases"]) == ["B", "C", "D", "E1"], "all four phases, row order"
    arms = {"B": "arm_state", "C": "arm_macro", "D": "arm_rel", "E1": "arm_prop"}
    for ph, arm in arms.items():
        entry = hr["phases"][ph]
        assert entry["arm_enhanced"] == arm
        assert entry["null_holds_both"] is True
        for h in ("h10", "h42"):
            assert set(entry[h]) == CELL_FIELDS, (ph, h)
            assert entry[h]["null_holds"] is True
    assert "arm_base" not in hr["phases"]["B"], "B/C/D share the plain base (no field)"
    assert hr["phases"]["E1"]["arm_base"] == "arm_base_self"
    assert hr["horizon_robust_all"] is True
    assert hr["null_criterion"] == NULL_CRITERION
    notes = hr["notes"]
    assert notes.startswith("Horizon-robustness sweep of the frozen h=21 Phase B/C/D nulls")
    assert len(notes) <= 500
    # Value pins (measured 2026-08-28 from ledger row ts 2026-07-30, 6 dp).
    assert hr["phases"]["B"]["h10"]["dm_p_mbb"] == 0.855572
    assert hr["phases"]["B"]["h42"]["mean_diff"] == -0.00468
    assert hr["phases"]["E1"]["h42"]["mean_diff"] == -0.00199
    assert hr["phases"]["D"]["h10"]["ci_lo"] == -0.012939


def test_horizon_robustness_regenerates_from_tracked_ledger(
    tmp_path, monkeypatch
) -> None:
    """Re-running the exporter against the TRACKED ledger (repo-root cwd — the
    ledger is a tracked file, not gitignored data) reproduces the committed
    panel exactly (modulo snapshot_ts) — no silent ledger/exporter drift, the
    display never outgrows its audit row."""
    committed = json.loads(PANEL.read_text(encoding="utf-8"))
    web = tmp_path / "web"
    web.mkdir()
    monkeypatch.setattr(et, "WEB", web)  # cwd stays at repo root → real ledger
    et.export_horizon_robustness()
    fresh = json.loads((web / "horizon_robustness.json").read_text(encoding="utf-8"))
    committed.pop("snapshot_ts", None)
    fresh.pop("snapshot_ts", None)
    assert fresh == committed


# --- export-lane registration (manifests + as_of + web barrel + i18n) ----------


def test_horizon_robustness_registered_in_manifests() -> None:
    """First-class citizen of the freshness map and the catalog (frozen)."""
    entry = next(
        (e for e in et._DATA_HEALTH_MANIFEST if e[0] == "horizon_robustness"), None
    )
    assert entry == ("horizon_robustness", "horizon_robustness.json", et._DH_FROZEN), (
        "derived from a tracked exploratory ledger row — moves only on a sweep re-run"
    )
    audit_idx = next(
        i for i, e in enumerate(et._DATA_HEALTH_MANIFEST) if e[0] == "ledger_audit"
    )
    assert et._DATA_HEALTH_MANIFEST.index(entry) == audit_idx + 1, (
        "registered directly after its ledger-neighbor"
    )
    license_, source = et._API_LICENSE["horizon_robustness"]
    assert license_ == "Aionis exploratory ledger row (repo PolyForm-NC)"
    assert "unverified" not in license_
    assert source == "horizon-robustness sweep summary of the frozen h=21 nulls"


def test_horizon_robustness_as_of_and_committed_manifests() -> None:
    """as_of = the row's own ledger ts (date part), wired into the committed
    data_health + api_catalog payloads."""
    assert et._dh_as_of("horizon_robustness", "horizon_robustness.json") == "2026-07-30"
    dh = json.loads((DATA / "data_health.json").read_text(encoding="utf-8"))
    panel = next((p for p in dh["panels"] if p["key"] == "horizon_robustness"), None)
    assert panel is not None, "must appear in the committed freshness map"
    assert panel["category"] == "frozen"
    assert panel["as_of"] == "2026-07-30"
    cat = json.loads((DATA / "api_catalog.json").read_text(encoding="utf-8"))
    ep = next((e for e in cat["endpoints"] if e["key"] == "horizon_robustness"), None)
    assert ep is not None and ep["status"] == "available"
    assert ep["freshness"] == "frozen"
    assert ep["license"] == "Aionis exploratory ledger row (repo PolyForm-NC)"


def test_horizon_robustness_registered_in_web_barrel_and_i18n() -> None:
    """The barrel types + registers the panel; the dict carries zh/en keys."""
    barrel = BARREL.read_text(encoding="utf-8")
    assert 'import horizonRobustnessJson from "./horizon_robustness.json";' in barrel
    assert "export type HorizonRobustness" in barrel
    assert "horizonRobustness: horizonRobustnessJson as HorizonRobustness," in barrel
    dict_src = DICT.read_text(encoding="utf-8")
    required = [
        "track.horizon.title",
        "track.horizon.desc",
        "track.horizon.col.phase",
        "track.horizon.col.diff",
        "track.horizon.col.ci",
        "track.horizon.col.dmp",
        "track.horizon.col.verdict",
        "track.horizon.verdict.holds",
        "track.horizon.note",
        "track.horizon.asof",
    ]
    for key in required:
        # zh + en blocks both carry the key (symmetric i18n contract).
        assert dict_src.count(f'"{key}"') == 2, key
