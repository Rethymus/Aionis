"""Contract tests for the model-inventory panel
(web/src/data/aionis/model_inventory.json).

TASK-H5: the SR 11-7 style model inventory — every ``confirmatory:first`` run
in the tracked ledger reconciled against its frozen ``runs/results/<sig>/``
directory (freeze→result row chain, H6 flag, aionis_version, differential
diff fields), plus the config-only commits listed honestly. Design:
reports/design/2026-08-29-model-card-design.md (SR 11-7 [B-tier]: governance
= inventory + card; H4 shipped the card, this ships the inventory).

Hermetic checks: the synthetic ledger + run tree are built INSIDE these tests
and used only as test fixtures (the one mock-like data the repo rules allow)
— exact row→directory mapping, freeze/result row-number parsing across a
blank ledger line, config_only classification (dirless confirmatory rows are
NOT config-only; locally-present configs are NOT config-only), honest nulls
for a missing directory / unreadable meta.json / missing diff keys, the
three-valued ``all_null_holds`` aggregate, the wrong-directory raise, SKIP
semantics, and the zero-clock LF output contract.

Committed-panel checks: the tracked JSON is reconciled against the tracked
ledger (row pairing, config_only classification, as_of) and — per the task
spec — against the frozen ``runs/results/`` tree on this machine (the four
Phase B/C/D/E1 directories; the diff numbers are recomputed from each
directory's differential.json, so this module requires that tree, present in
the dev worktree via a read-only junction into the main repo). Registration
in the freshness map / API catalog / web barrel / i18n dict is asserted on
both the code constants and the committed manifests. Zero skips, zero xfails.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

DATA = Path("web/src/data/aionis")
PANEL = DATA / "model_inventory.json"
BARREL = DATA / "index.ts"
VIEW = Path("web/src/components/model-health/model-health-view.tsx")
DICT = Path("web/src/i18n/dict.ts")
sys.path.insert(0, str(Path("scripts").resolve()))
import export_terminal_data as et  # noqa: E402

# --- fixture machinery (labeled synthetic test fixtures) ----------------------

SIG = "b" * 64  # confirmatory run WITH a local frozen directory (full diff)
PART_SIG = "c" * 64  # local directory, differential.json missing keys
GHOST_SIG = "d" * 64  # confirmatory run with NO local directory
NOCONF_SIG = "e" * 64  # config_committed WITH a local dir but NO confirmatory row
BAD_SIG = "f" * 64  # local directory whose meta.json is unreadable
CO_SIG = "a" * 64  # config_committed, no confirmatory row, no dir → config_only


def _meta(sig: str, ts: str) -> dict:
    return {
        "config_sig": sig,
        "h6_deterministic": True,
        "aionis_version": "0.1.0",
        "schema": 2,
        "ts": ts,
    }


# Full differential shaped like the real Phase C artifact (key names are the
# actual ones verified on the frozen directories).
DIFF_FULL: dict = {
    "n_months": 125,
    "mean_diff": -0.006487473568317837,
    "se_hac": 0.006654864630394057,
    "ci_half": 0.013043295000622688,
    "ci_lo": -0.019530768568940524,
    "ci_hi": 0.006555821432304851,
    "dm_stat": 1.036761419747237,
    "dm_p_mbb": 0.3553223388305847,
    "dm_flag": "ok",
    "publishable_ci_half": True,
    "null_holds": True,
}

# Partial differential: dm_p_mbb / null_holds absent → honest nulls.
DIFF_PARTIAL: dict = {
    "n_months": 125,
    "mean_diff": -0.0029798406036171702,
    "ci_lo": -0.013714495699179569,
    "ci_hi": 0.007754814491945227,
}


def _ledger_lines(*, holds: bool = True) -> list[str]:
    """Fixture ledger. Row numbering INCLUDES the blank line (row 3).

    Rows: 1 ingest noise · 2 config_committed CO_SIG (config-only candidate) ·
    3 blank · 4 freeze(SIG) · 5 result(SIG, dir present) · 6 freeze(PART) ·
    7 result(PART, partial diff) · 8 config_committed NOCONF (dir present, no
    result row → NOT config-only) · 9 freeze(GHOST) · 10 result(GHOST, no
    dir → honest nulls, NOT config-only) · 11 freeze(BAD) · 12 result(BAD,
    unreadable meta.json → honest nulls).
    """
    full = dict(DIFF_FULL)
    if not holds:
        full["null_holds"] = False
    return [
        json.dumps({"event": "data_ingest", "ts": "2026-01-01T00:00:00+00:00"}),
        json.dumps(
            {
                "event": "config_committed",
                "phase": "track_x",
                "ts": "2026-01-02T00:00:00+00:00",
                "config_sig": CO_SIG,
            }
        ),
        "",
        json.dumps(
            {
                "event": "config_committed",
                "phase": "B",
                "ts": "2026-01-04T00:00:00+00:00",
                "config_sig": SIG,
            }
        ),
        json.dumps(
            {
                "event": "confirmatory:first",
                "phase": "B",
                "ts": "2026-01-05T00:00:00+00:00",
                "config_sig": SIG,
            }
        ),
        json.dumps(
            {
                "event": "config_committed",
                "phase": "C",
                "ts": "2026-01-06T00:00:00+00:00",
                "config_sig": PART_SIG,
            }
        ),
        json.dumps(
            {
                "event": "confirmatory:first",
                "phase": "C",
                "ts": "2026-01-07T00:00:00+00:00",
                "config_sig": PART_SIG,
            }
        ),
        json.dumps(
            {
                "event": "config_committed",
                "phase": "ghost_dir",
                "ts": "2026-01-08T00:00:00+00:00",
                "config_sig": NOCONF_SIG,
            }
        ),
        json.dumps(
            {
                "event": "config_committed",
                "phase": "track_c",
                "ts": "2026-01-09T00:00:00+00:00",
                "config_sig": GHOST_SIG,
            }
        ),
        json.dumps(
            {
                "event": "confirmatory:first",
                "phase": "track_c",
                "ts": "2026-03-01T00:00:00+00:00",
                "config_sig": GHOST_SIG,
            }
        ),
        json.dumps(
            {
                "event": "config_committed",
                "phase": "bad",
                "ts": "2026-02-01T00:00:00+00:00",
                "config_sig": BAD_SIG,
            }
        ),
        json.dumps(
            {
                "event": "confirmatory:first",
                "phase": "bad",
                "ts": "2026-02-02T00:00:00+00:00",
                "config_sig": BAD_SIG,
            }
        ),
    ]


def _build_tree(tmp_path, *, ledger: list[str] | None = None, holds: bool = True) -> None:
    """Labeled synthetic fixture tree — the ONLY mock data these tests use."""
    runs = tmp_path / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "ledger.jsonl").write_text(
        "\n".join(ledger if ledger is not None else _ledger_lines()) + "\n",
        encoding="utf-8",
    )
    results = runs / "results"
    full = dict(DIFF_FULL)
    full["null_holds"] = holds
    for sig, meta, diff in (
        (SIG, _meta(SIG, "2026-01-05T00:00:00+00:00"), full),
        (PART_SIG, _meta(PART_SIG, "2026-01-07T00:00:00+00:00"), DIFF_PARTIAL),
        (NOCONF_SIG, _meta(NOCONF_SIG, "2026-01-08T00:00:00+00:00"), None),
    ):
        d = results / sig
        d.mkdir(parents=True)
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        if diff is not None:
            (d / "differential.json").write_text(json.dumps(diff), encoding="utf-8")
    bad = results / BAD_SIG
    bad.mkdir(parents=True)
    (bad / "meta.json").write_text("{not json", encoding="utf-8")  # unreadable
    web = tmp_path / "web" / "src" / "data" / "aionis"
    web.mkdir(parents=True)


def _run_export(
    tmp_path, monkeypatch, *, ledger: list[str] | None = None, holds: bool = True
) -> dict:
    _build_tree(tmp_path, ledger=ledger, holds=holds)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(et, "WEB", tmp_path / "web" / "src" / "data" / "aionis")
    et.export_model_inventory()
    return json.loads(
        (tmp_path / "web" / "src" / "data" / "aionis" / "model_inventory.json")
        .read_text(encoding="utf-8")
    )


def _assert_no_clock(payload: dict) -> None:
    """Zero-clock contract: no snapshot timestamp anywhere in the inventory."""

    def _walk(o: object) -> None:
        if isinstance(o, dict):
            assert "snapshot_ts" not in o, "the inventory is a zero-clock panel"
            for v in o.values():
                _walk(v)
        elif isinstance(o, list):
            for v in o:
                _walk(v)

    _walk(payload)


# --- exporter exact-value locks (synthetic fixtures) --------------------------


def test_inventory_maps_rows_and_dirs_verbatim(tmp_path, monkeypatch) -> None:
    """Run rows map the ledger + frozen directories byte-for-byte; freeze/
    result row numbers survive the blank ledger line; numbers round 6 dp."""
    inv = _run_export(tmp_path, monkeypatch)
    assert inv["model_inventory_version"] == et.MODEL_INVENTORY_VERSION == "v1"
    assert inv["status"] == "ok"
    # 4 confirmatory:first rows → 4 inventory runs, ledger order preserved.
    assert [r["phase"] for r in inv["runs"]] == ["B", "C", "track_c", "bad"]
    sig_run, part_run, ghost_run, bad_run = inv["runs"]

    # SIG: full mapping — freeze/result row numbers + ts + meta + diff.
    assert sig_run["config_sig"] == SIG
    assert sig_run["freeze_row"] == 4
    assert sig_run["freeze_ts"] == "2026-01-04T00:00:00+00:00"
    assert sig_run["result_row"] == 5
    assert sig_run["result_ts"] == "2026-01-05T00:00:00+00:00"
    assert sig_run["local_dir_present"] is True
    assert sig_run["h6_deterministic"] is True
    assert sig_run["aionis_version"] == "0.1.0"
    assert sig_run["run_ts"] == "2026-01-05T00:00:00+00:00"
    assert sig_run["diff"] == {
        "mean_diff": round(DIFF_FULL["mean_diff"], 6),
        "ci_lo": round(DIFF_FULL["ci_lo"], 6),
        "ci_hi": round(DIFF_FULL["ci_hi"], 6),
        "dm_p_mbb": round(DIFF_FULL["dm_p_mbb"], 6),
        "null_holds": True,
    }

    # PART: differential.json missing dm_p_mbb/null_holds → honest nulls.
    assert part_run["freeze_row"] == 6 and part_run["result_row"] == 7
    assert part_run["local_dir_present"] is True
    assert part_run["diff"] == {
        "mean_diff": round(DIFF_PARTIAL["mean_diff"], 6),
        "ci_lo": round(DIFF_PARTIAL["ci_lo"], 6),
        "ci_hi": round(DIFF_PARTIAL["ci_hi"], 6),
        "dm_p_mbb": None,
        "null_holds": None,
    }

    # GHOST: no local directory → every artifact-derived field an honest null.
    assert ghost_run["freeze_row"] == 9 and ghost_run["result_row"] == 10
    assert ghost_run["local_dir_present"] is False
    assert ghost_run["h6_deterministic"] is None
    assert ghost_run["aionis_version"] is None
    assert ghost_run["run_ts"] is None
    assert ghost_run["diff"] is None

    # BAD: directory present but meta.json unreadable → honest unknown too.
    assert bad_run["result_row"] == 12
    assert bad_run["local_dir_present"] is False
    assert bad_run["h6_deterministic"] is None
    assert bad_run["diff"] is None

    # as_of = the newest covered LEDGER ts (row 10), never a clock.
    assert inv["as_of"] == "2026-03-01T00:00:00+00:00"
    # summary: counted from the scan, never declared.
    assert inv["summary"] == {
        "n_confirmatory_runs": 4,
        "n_local_dirs": 2,
        "n_config_only": 1,
        "all_null_holds": True,
    }
    assert "SR 11-7" in inv["notes"]
    assert "read-only" in inv["notes"].lower()
    assert "honest unknown" in inv["notes"]
    assert inv["provenance"]["regen_command"].count("export_model_inventory") == 1
    _assert_no_clock(inv)


def test_config_only_classification(tmp_path, monkeypatch) -> None:
    """config_committed rows: no confirmatory:first AND no local dir →
    config_only. A dirless confirmatory row is NOT config-only (it IS a run,
    honestly listed there); a locally-present config without a result row is
    NOT config-only either (its artifacts exist)."""
    inv = _run_export(tmp_path, monkeypatch)
    co = inv["config_only"]
    assert len(co) == 1
    assert co[0] == {
        "phase": "track_x",
        "config_sig": CO_SIG,
        "row": 2,
        "ts": "2026-01-02T00:00:00+00:00",
    }
    assert CO_SIG not in {r["config_sig"] for r in inv["runs"]}
    run_sigs = {r["config_sig"] for r in inv["runs"]}
    assert GHOST_SIG in run_sigs, "dirless confirmatory stays in runs, honest nulls"
    assert NOCONF_SIG not in {c["config_sig"] for c in co}, (
        "locally-present config without a result row is not config-only"
    )


def test_all_null_holds_explicit_false_breaks_aggregate(tmp_path, monkeypatch) -> None:
    """A diff that explicitly records null_holds=false sinks the aggregate."""
    inv = _run_export(tmp_path, monkeypatch, holds=False)
    assert inv["runs"][0]["diff"]["null_holds"] is False
    assert inv["summary"]["all_null_holds"] is False


def test_wrong_directory_sig_raises(tmp_path, monkeypatch) -> None:
    """meta.json.config_sig != ledger sig → raise (wrong/corrupted dir guard)."""
    _build_tree(tmp_path)
    tampered = tmp_path / "runs" / "results" / SIG / "meta.json"
    meta = json.loads(tampered.read_text(encoding="utf-8"))
    meta["config_sig"] = GHOST_SIG
    tampered.write_text(json.dumps(meta), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(et, "WEB", tmp_path / "web" / "src" / "data" / "aionis")
    with pytest.raises(ValueError, match="wrong/corrupted run directory"):
        et.export_model_inventory()


def test_absent_sources_skip_via_safe_export(tmp_path, monkeypatch, capsys) -> None:
    """No ledger, or a ledger without confirmatory:first rows → FileNotFoundError,
    so _safe_export skips and the tracked JSON retains its committed value."""
    runs = tmp_path / "runs"
    runs.mkdir(parents=True)
    (runs / "ledger.jsonl").write_text(
        json.dumps(
            {
                "event": "config_committed",
                "phase": "B",
                "ts": "2026-01-01T00:00:00+00:00",
                "config_sig": CO_SIG,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(et, "WEB", tmp_path / "web" / "src" / "data" / "aionis")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        et.export_model_inventory()

    # (b) ledger absent entirely (fresh CI checkout — runs/ is not exported).
    empty = tmp_path / "checkout_without_ledger"
    empty.mkdir()
    monkeypatch.chdir(empty)
    with pytest.raises(FileNotFoundError):
        et.export_model_inventory()
    # (c) the _safe_export guard swallows exactly this failure + logs the skip.
    assert et._safe_export("model_inventory", et.export_model_inventory) is None
    assert "SKIP model_inventory" in capsys.readouterr().out


def test_output_is_lf_bytes(tmp_path, monkeypatch) -> None:
    """The inventory file is written LF-only (byte-stable contract)."""
    _build_tree(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(et, "WEB", tmp_path / "web" / "src" / "data" / "aionis")
    et.export_model_inventory()
    raw = (
        (tmp_path / "web" / "src" / "data" / "aionis" / "model_inventory.json")
        .read_bytes()
    )
    assert b"\r" not in raw


# --- committed panel (tracked JSON, reconciled against tracked artifacts) -----


def _load() -> dict:
    return json.loads(PANEL.read_text(encoding="utf-8"))


def _tracked_rows() -> list[tuple[int, dict]]:
    lines = Path("runs/ledger.jsonl").read_text(encoding="utf-8").splitlines()
    return [(i, json.loads(line)) for i, line in enumerate(lines, 1) if line.strip()]


def test_committed_inventory_shape_and_ledger_reconcile() -> None:
    """runs == 5 (B/C/D/E1/track_c), local dirs == 4, config_only == 11 — and
    every row re-derived from the TRACKED ledger by the pairing rule."""
    inv = _load()
    assert inv["model_inventory_version"] == "v1"
    assert inv["status"] == "ok"
    assert inv["summary"] == {
        "n_confirmatory_runs": 5,
        "n_local_dirs": 4,
        "n_config_only": 11,
        "all_null_holds": None,  # the frozen differential.json files carry no null_holds
    }
    assert [r["phase"] for r in inv["runs"]] == ["B", "C", "D", "E1", "track_c"]
    local = [r for r in inv["runs"] if r["local_dir_present"]]
    assert len(local) == 4
    assert {r["phase"] for r in local} == {"B", "C", "D", "E1"}
    track_c = inv["runs"][-1]
    assert track_c["local_dir_present"] is False
    assert track_c["h6_deterministic"] is None
    assert track_c["aionis_version"] is None
    assert track_c["run_ts"] is None
    assert track_c["diff"] is None
    for r in local:
        assert r["h6_deterministic"] is True
        assert r["freeze_row"] < r["result_row"], "config_committed BEFORE result"

    # Re-derive every run row from the tracked ledger (same pairing rule).
    rows = _tracked_rows()
    for r in inv["runs"]:
        results = [
            (i, d)
            for i, d in rows
            if d.get("event") == "confirmatory:first"
            and d.get("config_sig") == r["config_sig"]
        ]
        assert len(results) == 1, r["config_sig"]
        lineno, rec = results[0]
        assert r["result_row"] == lineno
        assert r["result_ts"] == rec.get("ts")
        assert r["phase"] == rec.get("phase")
        freezes = [
            (i, d)
            for i, d in rows
            if i < lineno
            and d.get("event") == "config_committed"
            and d.get("config_sig") == r["config_sig"]
        ]
        assert freezes, f"freeze row must exist for {r['config_sig']}"
        assert r["freeze_row"] == freezes[-1][0]
        assert r["freeze_ts"] == freezes[-1][1].get("ts")

    # Re-derive config_only from the tracked ledger (same classification rule).
    confirmed = {r["config_sig"] for r in inv["runs"]}
    expect_co = []
    for i, d in rows:
        if d.get("event") != "config_committed":
            continue
        sig = str(d.get("config_sig") or "")
        if sig in confirmed:
            continue
        if (Path("runs/results") / sig / "meta.json").exists():
            continue
        expect_co.append(
            {"phase": d.get("phase"), "config_sig": sig, "row": i, "ts": d.get("ts")}
        )
    assert inv["config_only"] == expect_co
    assert len(inv["config_only"]) == 11
    # phases measured on 2026-08-29: track_b×3, baseline_ff5×1, baseline_rank×2,
    # track_c×2 (superseded), track_adaptive×3.
    co_phases = [c["phase"] for c in inv["config_only"]]
    assert co_phases == [
        "track_b",
        "track_b",
        "track_b",
        "baseline_ff5",
        "baseline_rank",
        "baseline_rank",
        "track_c",
        "track_c",
        "track_adaptive",
        "track_adaptive",
        "track_adaptive",
    ]

    # as_of = the newest covered ledger ts, recomputed.
    covered = [r["result_ts"] for r in inv["runs"]]
    covered += [r["freeze_ts"] for r in inv["runs"] if r["freeze_ts"] is not None]
    covered += [c["ts"] for c in inv["config_only"]]
    assert inv["as_of"] == max(covered)
    assert "SR 11-7" in inv["notes"]
    assert "read-only" in inv["notes"].lower()
    assert "honest unknown" in inv["notes"]
    _assert_no_clock(inv)


def test_committed_diff_recomputes_from_frozen_dirs() -> None:
    """The diff numbers equal each frozen directory's differential.json,
    re-read and re-rounded (runs/ read-only; the four B/C/D/E1 directories on
    this machine are the inventory's local reality — track_c honestly null)."""
    inv = _load()
    for r in inv["runs"]:
        run_dir = Path("runs/results") / r["config_sig"]
        if not r["local_dir_present"]:
            assert r["diff"] is None, r["config_sig"]
            continue
        raw = json.loads((run_dir / "differential.json").read_text(encoding="utf-8"))
        meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
        assert r["h6_deterministic"] == (
            meta.get("h6_deterministic") if isinstance(
                meta.get("h6_deterministic"), bool
            ) else None
        )
        assert r["aionis_version"] == meta.get("aionis_version")
        assert r["run_ts"] == meta.get("ts")
        assert set(r["diff"]) == {"mean_diff", "ci_lo", "ci_hi", "dm_p_mbb", "null_holds"}
        for field in ("mean_diff", "ci_lo", "ci_hi", "dm_p_mbb"):
            v = raw.get(field)
            if isinstance(v, bool) or not isinstance(v, int | float):
                expect = None
            elif math.isfinite(v):
                expect = round(float(v), 6)
            else:
                expect = None
            assert r["diff"][field] == expect, (r["config_sig"], field)
        nh = raw.get("null_holds")
        assert r["diff"]["null_holds"] == (nh if isinstance(nh, bool) else None)
    # the local reality is exactly the four frozen Phase directories
    dirs = {
        p.name
        for p in Path("runs/results").iterdir()
        if (p / "meta.json").exists()
    }
    assert dirs == {r["config_sig"] for r in inv["runs"] if r["local_dir_present"]}


# --- export-lane registration (manifests + as_of + web barrel + i18n) ----------


def test_committed_inventory_registered_everywhere() -> None:
    """First-class citizen of the freshness map, the API catalog, the barrel
    and the i18n dict — asserted on the code constants AND the committed
    manifests (the three-place sync rule of TASK-H2)."""
    entry = next(
        (e for e in et._DATA_HEALTH_MANIFEST if e[0] == "model_inventory"), None
    )
    assert entry == ("model_inventory", "model_inventory.json", et._DH_FROZEN), (
        "derived from the tracked ledger + frozen artifacts — frozen, zero-clock"
    )
    card_idx = next(
        i for i, e in enumerate(et._DATA_HEALTH_MANIFEST) if e[0] == "model_card"
    )
    assert et._DATA_HEALTH_MANIFEST.index(entry) == card_idx + 1, (
        "registered directly after its H4 sibling"
    )
    assert et._API_LICENSE["model_inventory"] == (
        "Aionis research artifacts (repo MIT)",
        "SR 11-7 style model inventory over the tracked ledger and frozen run directories",
    )

    inv = _load()
    as_of_date = inv["as_of"].split("T")[0]
    assert et._dh_as_of("model_inventory", "model_inventory.json") == as_of_date
    dh = json.loads((DATA / "data_health.json").read_text(encoding="utf-8"))
    panel = next((p for p in dh["panels"] if p["key"] == "model_inventory"), None)
    assert panel is not None, "must appear in the committed freshness map"
    assert panel["category"] == "frozen"
    assert panel["as_of"] == as_of_date
    assert panel["present"] is True
    cat = json.loads((DATA / "api_catalog.json").read_text(encoding="utf-8"))
    ep = next((e for e in cat["endpoints"] if e["key"] == "model_inventory"), None)
    assert ep is not None and ep["status"] == "available"
    assert ep["freshness"] == "frozen"
    assert ep["license"] == "Aionis research artifacts (repo MIT)"

    barrel = BARREL.read_text(encoding="utf-8")
    assert 'import modelInventoryJson from "./model_inventory.json";' in barrel
    assert "export type ModelInventoryRun" in barrel
    assert "export type ModelInventory" in barrel
    assert "modelInventory: modelInventoryJson as ModelInventory," in barrel
    view = VIEW.read_text(encoding="utf-8")
    assert "ModelInventorySection" in view
    assert view.index("<ModelInventorySection />") > view.index(
        "<ModelCardSection />"
    ), "the inventory section renders after the model card section"

    dict_src = DICT.read_text(encoding="utf-8")
    required = [
        "inventory.title",
        "inventory.subtitle",
        "inventory.empty",
        "inventory.col.phase",
        "inventory.col.sig",
        "inventory.col.freezeTs",
        "inventory.col.h6",
        "inventory.col.diff",
        "inventory.col.verdict",
        "inventory.col.local",
        "inventory.verdict.holds",
        "inventory.verdict.broken",
        "inventory.verdict.unknown",
        "inventory.local.missing",
        "inventory.configOnly",
        "inventory.configOnlyNote",
        "inventory.asof",
        "inventory.disclaimer",
    ]
    for key in required:
        # zh + en blocks both carry the key (symmetric i18n contract).
        assert dict_src.count(f'"{key}"') == 2, key
