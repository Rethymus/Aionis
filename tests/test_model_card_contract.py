"""Contract tests for the model-card panel (web/src/data/aionis/model_card.json).

TASK-H4: the card is the machine-readable, hash-pinned record of the frozen
confirmatory model (identity / data / model / evaluation protocol / headline
results / ledger governance), lifted from the gitignored
``runs/results/<config_sig>/`` artifacts + the tracked headline metrics + the
tracked ledger. Design: reports/design/2026-08-29-model-card-design.md.

Hermetic checks: the synthetic run tree is built INSIDE these tests and used
only as test fixtures (the one mock-like data the repo rules allow) — exact
section-by-section value pins, both self-check raises (wrong-directory sig,
drifted uv.lock), the disclosed-drift path, and the SKIP semantics of
``_safe_export`` on a cold tree.

Committed-panel checks: reconciled against TRACKED artifacts only
(metrics.json, runs/ledger.jsonl, uv.lock, docs/track-c-preregistration.md,
data_health.json, api_catalog.json) so they run on a fresh CI checkout without
the gitignored runs/results/ tree. Zero skips, zero xfails.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

DATA = Path("web/src/data/aionis")
PANEL = DATA / "model_card.json"
sys.path.insert(0, str(Path("scripts").resolve()))
import export_terminal_data as et  # noqa: E402

# --- fixture machinery (labeled synthetic test fixtures) ----------------------


def _sha_lf(b: bytes) -> str:
    """sha256 over canonical LF bytes — mirrors the exporter's tracked-file pin."""
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


SIG = hashlib.sha256(b"aionis-model-card-fixture-run").hexdigest()
GHOST_SIG = hashlib.sha256(b"aionis-model-card-fixture-ghost").hexdigest()

UV_LOCK = (
    b'name = "aionis"\nversion = "0.1.0"\n\n[[package]]\n'
    b'name = "lightgbm"\nversion = "4.7.0"\n'
)
PREREG = (
    b"# Track C pre-registration (fixture)\n\n"
    b"Two-tailed null-expected rank-IC claim, frozen before any OOS "
    b"observation.\n"
)

CFG: dict = {
    "feature_cols": [
        "mktcap",
        "pb_ratio",
        "roa",
        "fund_assets",
        "fund_revenue",
        "fund_net_income",
        "fund_equity",
        "fund_shares_out",
        "fund_long_term_debt",
    ],
    "horizon": 21,
    "n_splits": 5,
    "embargo_sessions": 21,
    "cv_scheme": "5-fold PurgedGroupKFold (group=month, embargo=21 sessions) fixture",
    "frozen_params": {
        "objective": "regression",
        "n_estimators": 500,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "min_child_samples": 20,
        "reg_lambda": 1.0,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 1,
        "n_jobs": 1,
        "random_state": 0,
        "bagging_seed": 0,
        "feature_fraction_seed": 0,
        "drop_seed": 0,
        "verbose": -1,
    },
    "end_lag_months": {"10-K": 6, "10-Q": 4},
    "versions": {"lightgbm": "4.7.0", "purgedcv": "0.1.2", "arch": "8.0.0"},
    "fund_sha256": "f" * 64,
    "prices_sha256": "e" * 64,
    "membership_sha256": "d" * 64,
}
CFG["uv_lock_sha256"] = _sha_lf(UV_LOCK)

META = {
    "config_sig": SIG,
    "h6_deterministic": True,
    "aionis_version": "0.1.0",
    "schema": 1,
    "ts": "2026-01-05T04:27:39+00:00",
}

METRICS = {
    "combined_ic": -0.0088,
    "p": 0.484,
    "n_months": 71,
    "ci_lo": -0.0336,
    "ci_hi": 0.0159,
    "verdict": "NULL",
    "jt_look1": "NOT_EQUIVALENT",
    "h6": "PASS",
    "sesoi": 0.01,
    "latest_month": "2026-08-03",
    "n_picks_total": 0,
    "ledger_row": 49,
    "config_sig_short": "e14b9d44",
    "snapshot_ts": "2026-08-22T13:32:20.445645+00:00",
}


def _ledger_lines() -> list[str]:
    """Fixture ledger: row numbering INCLUDES the blank line (row 3).

    Rows: 1 data_ingest noise · 2 confirmatory row whose run dir is absent
    (must be skipped) · 3 blank · 4 freeze(config_committed, SIG) ·
    5 result(confirmatory:first, SIG) · 6 a NEWER track_c freeze whose run dir
    is also absent (must not hijack resolution).
    """
    return [
        json.dumps({"event": "data_ingest", "ts": "2026-01-01T00:00:00+00:00"}),
        json.dumps(
            {
                "event": "confirmatory:first",
                "phase": "A0",
                "ts": "2026-01-02T00:00:00+00:00",
                "config_sig": GHOST_SIG,
            }
        ),
        "",
        json.dumps(
            {
                "event": "config_committed",
                "phase": "B",
                "ts": "2026-01-04T04:15:16+00:00",
                "config_sig": SIG,
                "config": CFG,
            }
        ),
        json.dumps(
            {
                "event": "confirmatory:first",
                "phase": "B",
                "ts": "2026-01-05T04:27:39+00:00",
                "config_sig": SIG,
                "combined_ic": {"mean": -0.0088},
            }
        ),
        json.dumps(
            {
                "event": "config_committed",
                "phase": "track_c",
                "ts": "2026-02-01T00:00:00+00:00",
                "config_sig": GHOST_SIG,
            }
        ),
    ]


def _build_tree(
    tmp_path,
    *,
    meta_sig: str | None = None,
    with_results_dir: bool = True,
    uv_lock: bytes | None = UV_LOCK,
    with_metrics: bool = True,
    with_prereg: bool = True,
    with_ledger: bool = True,
) -> None:
    """Labeled synthetic fixture tree — the ONLY mock data these tests use."""
    if with_results_dir:
        run_dir = tmp_path / "runs" / "results" / SIG
        run_dir.mkdir(parents=True)
        (run_dir / "config.json").write_text(json.dumps(CFG), encoding="utf-8")
        meta = dict(META)
        if meta_sig is not None:
            meta["config_sig"] = meta_sig
        (run_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    if with_ledger:
        (tmp_path / "runs").mkdir(exist_ok=True)
        (tmp_path / "runs" / "ledger.jsonl").write_text(
            "\n".join(_ledger_lines()) + "\n", encoding="utf-8"
        )
    if uv_lock is not None:
        (tmp_path / "uv.lock").write_bytes(uv_lock)
    if with_metrics:
        web = tmp_path / "web" / "src" / "data" / "aionis"
        web.mkdir(parents=True)
        (web / "metrics.json").write_text(json.dumps(METRICS), encoding="utf-8")
    if with_prereg:
        (tmp_path / "docs").mkdir(exist_ok=True)
        (tmp_path / "docs" / "track-c-preregistration.md").write_bytes(PREREG)


def _run_export(tmp_path, monkeypatch, **kwargs) -> dict:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(et, "WEB", tmp_path / "web" / "src" / "data" / "aionis")
    et.export_model_card(**kwargs)
    out = tmp_path / "web" / "src" / "data" / "aionis" / "model_card.json"
    return json.loads(out.read_text(encoding="utf-8"))


def _assert_no_clock(payload: dict) -> None:
    """Zero-clock contract: no snapshot timestamp anywhere in the card."""
    def _walk(o: object) -> None:
        if isinstance(o, dict):
            assert "snapshot_ts" not in o, "the card is a zero-clock panel"
            for v in o.values():
                _walk(v)
        elif isinstance(o, list):
            for v in o:
                _walk(v)

    _walk(payload)


# --- exporter exact-value locks (synthetic fixtures) --------------------------


def test_card_sections_fields_verbatim(tmp_path, monkeypatch) -> None:
    """Every section field is the fixture artifact value, byte-for-byte."""
    _build_tree(tmp_path)
    card = _run_export(tmp_path, monkeypatch)

    assert card["model_card_version"] == et.MODEL_CARD_VERSION == "v1"
    # identity — resolved from the ledger row + meta.json (never a clock)
    assert card["identity"] == {
        "phase": "B",
        "config_sig": SIG,
        "config_sig_short": SIG[:8],
        "results_dir": f"runs/results/{SIG}",
        "aionis_version": "0.1.0",
        "schema": 1,
        "h6_deterministic": True,
        "run_ts": META["ts"],
    }
    # data — verbatim config.json pins
    assert card["data"]["fund_sha256"] == "f" * 64
    assert card["data"]["prices_sha256"] == "e" * 64
    assert card["data"]["membership_sha256"] == "d" * 64
    assert card["data"]["end_lag_months"] == {"10-K": 6, "10-Q": 4}
    assert card["data"]["feature_cols"] == CFG["feature_cols"]
    assert card["data"]["feature_cols_n"] == 9 == len(CFG["feature_cols"])
    # model — full frozen_params dict verbatim + determinism lift
    assert card["model"]["learner"] == "lightgbm"
    assert card["model"]["learner_version"] == "4.7.0"
    assert card["model"]["versions"] == CFG["versions"]
    assert card["model"]["frozen_params"] == CFG["frozen_params"]
    assert card["model"]["determinism"] == {
        "random_state": 0,
        "bagging_seed": 0,
        "feature_fraction_seed": 0,
        "drop_seed": 0,
        "n_jobs": 1,
    }
    # evaluation protocol — verbatim
    assert card["evaluation_protocol"] == {
        "cv_scheme": CFG["cv_scheme"],
        "horizon": 21,
        "n_splits": 5,
        "embargo_sessions": 21,
    }
    # results — the headline metrics embedded VERBATIM (byte-identical values)
    assert card["results"]["source"] == "web/src/data/aionis/metrics.json"
    for field in et._CARD_RESULT_FIELDS:
        assert card["results"][field] == METRICS[field], field
    assert card["results"]["combined_ic"] == -0.0088
    assert card["results"]["ledger_row"] == 49
    assert card["results"]["config_sig_short"] == "e14b9d44"
    # governance — freeze/result chain of THIS card's sig (rows 4/5: the blank
    # ledger line occupies row 3 and must keep numbering intact)
    freeze = card["governance"]["ledger_freeze_row"]
    assert freeze["row"] == 4
    assert freeze["ts"] == "2026-01-04T04:15:16+00:00"
    assert freeze["line_sha256"] == _sha_lf(_ledger_lines()[3].encode("utf-8"))
    assert card["governance"]["ledger_result_row"]["row"] == 5
    # uv.lock — matching fixture → match, no drift note
    assert card["governance"]["uv_lock_sha256"] == _sha_lf(UV_LOCK)
    assert card["governance"]["uv_lock_recomputed_sha256"] == _sha_lf(UV_LOCK)
    assert card["governance"]["uv_lock_match"] is True
    assert card["governance"]["uv_lock_note"] is None
    # intended_use — prereg doc pinned by its content sha
    assert card["intended_use"]["prereg"]["path"] == "docs/track-c-preregistration.md"
    assert card["intended_use"]["prereg"]["sha256"] == _sha_lf(PREREG)
    assert card["intended_use"]["display_only"] is True
    assert card["intended_use"]["not_investment_advice"] is True
    # provenance — S-numbered sources, config.json pinned by its file sha
    sids = [s["sid"] for s in card["provenance"]["sources"]]
    assert sids == ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]
    s1 = card["provenance"]["sources"][0]
    assert s1["locator"] == f"runs/results/{SIG}/config.json"
    assert s1["integrity"] == (
        "sha256:"
        + hashlib.sha256(json.dumps(CFG).encode("utf-8")).hexdigest()
        + " (file bytes)"
    )
    _assert_no_clock(card)


def test_card_resolution_skips_dirless_confirmatory_rows(tmp_path, monkeypatch) -> None:
    """Confirmatory rows without local artifacts never hijack the resolution.

    The fixture ledger carries a confirmatory row (line 2) and a NEWER freeze
    row (line 6) for GHOST_SIG with no runs/results/<sig>/ dir; the card must
    resolve the chronologically-first row that DOES resolve (line 5, SIG)."""
    _build_tree(tmp_path)
    card = _run_export(tmp_path, monkeypatch)
    assert card["identity"]["config_sig"] == SIG
    assert card["identity"]["phase"] == "B"
    assert card["governance"]["ledger_result_row"]["row"] == 5


def test_wrong_directory_sig_raises(tmp_path, monkeypatch) -> None:
    """meta.json.config_sig != ledger sig → raise (wrong/corrupted dir guard)."""
    _build_tree(tmp_path, meta_sig=GHOST_SIG)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(et, "WEB", tmp_path / "web" / "src" / "data" / "aionis")
    with pytest.raises(ValueError, match="wrong/corrupted run directory"):
        et.export_model_card()


def test_uv_lock_drift_raises_and_disclosed_path(tmp_path, monkeypatch) -> None:
    """Drifted uv.lock: strict raise by default; disclosed regeneration opt-in."""
    tampered = UV_LOCK + b"# drifted dependency added later\n"
    _build_tree(tmp_path, uv_lock=tampered)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(et, "WEB", tmp_path / "web" / "src" / "data" / "aionis")
    with pytest.raises(ValueError, match="uv.lock"):
        et.export_model_card()

    card = _run_export(tmp_path, monkeypatch, allow_uv_lock_drift=True)
    assert card["governance"]["uv_lock_sha256"] == _sha_lf(UV_LOCK)
    assert card["governance"]["uv_lock_recomputed_sha256"] == _sha_lf(tampered)
    assert card["governance"]["uv_lock_match"] is False
    assert card["governance"]["uv_lock_note"] is not None
    assert "drift" in card["governance"]["uv_lock_note"].lower()


def test_missing_sources_skip(tmp_path, monkeypatch, capsys) -> None:
    """Cold tree → FileNotFoundError → _safe_export SKIP (tracked JSON wins)."""
    _build_tree(tmp_path, with_results_dir=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(et, "WEB", tmp_path / "web" / "src" / "data" / "aionis")
    with pytest.raises(FileNotFoundError):
        et.export_model_card()
    assert et._safe_export("model_card", et.export_model_card) is None
    captured = capsys.readouterr()
    assert "SKIP model_card" in captured.out
    assert not (tmp_path / "web" / "src" / "data" / "aionis" / "model_card.json").exists()

    # every other machine-read source is load-bearing the same way
    for case in (
        {"with_ledger": False},
        {"uv_lock": None},
        {"with_metrics": False},
        {"with_prereg": False},
    ):
        tmp2 = tmp_path / f"case_{next(iter(case))}"
        _build_tree(tmp2, **case)
        monkeypatch.chdir(tmp2)
        monkeypatch.setattr(et, "WEB", tmp2 / "web" / "src" / "data" / "aionis")
        with pytest.raises(FileNotFoundError):
            et.export_model_card()


def test_config_without_frozen_uv_lock_is_honest_null(tmp_path, monkeypatch) -> None:
    """No frozen uv_lock_sha256 in the config → match null, NO drift note."""
    _build_tree(tmp_path)
    cfg_path = tmp_path / "runs" / "results" / SIG / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    del cfg["uv_lock_sha256"]
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    card = _run_export(tmp_path, monkeypatch)
    assert card["governance"]["uv_lock_sha256"] is None
    assert card["governance"]["uv_lock_match"] is None
    assert card["governance"]["uv_lock_note"] is None


def test_output_is_lf_bytes(tmp_path, monkeypatch) -> None:
    """The card file is written LF-only (byte-stable contract)."""
    _build_tree(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(et, "WEB", tmp_path / "web" / "src" / "data" / "aionis")
    et.export_model_card()
    raw = (tmp_path / "web" / "src" / "data" / "aionis" / "model_card.json").read_bytes()
    assert b"\r" not in raw


# --- committed panel (tracked JSON, reconciled against tracked artifacts) -----


def _load() -> dict:
    return json.loads(PANEL.read_text(encoding="utf-8"))


SECTIONS = {
    "model_card_version",
    "identity",
    "intended_use",
    "data",
    "model",
    "evaluation_protocol",
    "results",
    "governance",
    "provenance",
}


def test_committed_card_shape_and_results_reconcile_metrics() -> None:
    """Section contract + the results section equals metrics.json verbatim."""
    card = _load()
    assert set(card) == SECTIONS
    assert card["model_card_version"] == "v1"
    metrics = json.loads((DATA / "metrics.json").read_text(encoding="utf-8"))
    for field in et._CARD_RESULT_FIELDS:
        assert card["results"][field] == metrics[field], (
            f"results.{field} must be the metrics.json value verbatim"
        )
    assert card["results"]["combined_ic"] == -0.0088
    assert card["results"]["ledger_row"] == 49
    assert card["results"]["config_sig_short"] == "e14b9d44"
    assert card["results"]["n_months"] == 71
    assert card["results"]["verdict"] == "NULL"
    assert card["results"]["sesoi"] == 0.01
    # the embedded headline's own trace label resolves in the tracked ledger
    rows = [
        json.loads(line)
        for line in Path("runs/ledger.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    climax = rows[card["results"]["ledger_row"] - 1]
    assert climax["event"] == "confirmatory:first"
    assert climax["phase"] == "track_c"
    assert climax["config_sig"].startswith(card["results"]["config_sig_short"])
    _assert_no_clock(card)


def test_committed_card_ledger_chain_verifiable() -> None:
    """Freeze→result governance chain re-verified against the raw ledger."""
    card = _load()
    lines = Path("runs/ledger.jsonl").read_text(encoding="utf-8").splitlines()
    sig = card["identity"]["config_sig"]
    freeze = card["governance"]["ledger_freeze_row"]
    result = card["governance"]["ledger_result_row"]
    assert result["row"] > freeze["row"], "config_committed BEFORE result"
    freeze_rec = json.loads(lines[freeze["row"] - 1])
    result_rec = json.loads(lines[result["row"] - 1])
    assert freeze_rec["event"] == "config_committed"
    assert result_rec["event"] == "confirmatory:first"
    assert freeze_rec["config_sig"] == result_rec["config_sig"] == sig
    assert freeze["ts"] == freeze_rec["ts"]
    assert freeze["line_sha256"] == hashlib.sha256(
        lines[freeze["row"] - 1].encode("utf-8")
    ).hexdigest()
    assert freeze_rec["ts"] <= result_rec["ts"], "freeze precedes its result"
    assert card["identity"]["results_dir"] == f"runs/results/{sig}"


def test_committed_card_hashes_recomputed() -> None:
    """Content pins recomputed from the tracked repo files; drift disclosed.

    Measured on 2026-08-29: uv.lock has drifted since the Phase-line freeze
    (later display/research lanes added dependencies), so the card carries the
    frozen hash + the current hash + match=false + a drift note. A re-freeze
    that changes this pin is a conscious contract re-pin, not silent drift.
    """
    card = _load()
    assert card["intended_use"]["prereg"]["sha256"] == _sha_lf(
        Path("docs/track-c-preregistration.md").read_bytes()
    )
    assert (
        card["governance"]["uv_lock_recomputed_sha256"]
        == _sha_lf(Path("uv.lock").read_bytes())
    )
    # Measured 2026-08-29: the lock the run was frozen with (uv.lock at the
    # freeze commit, 2026-07-28) — pinned here against silent drift.
    frozen_uv = "e045a023c5ea8d9a91ef41f183dc95447f61788d79c5fa974229c7b32d5b34a0"
    assert card["governance"]["uv_lock_sha256"] == frozen_uv
    assert card["governance"]["uv_lock_match"] is False
    assert card["governance"]["uv_lock_note"] is not None
    # the frozen training env stays pinned regardless of the lock drift
    assert card["model"]["determinism"] == {
        "random_state": 0,
        "bagging_seed": 0,
        "feature_fraction_seed": 0,
        "drop_seed": 0,
        "n_jobs": 1,
    }
    assert card["model"]["learner"] == "lightgbm"
    assert card["model"]["versions"] == {
        "lightgbm": "4.7.0",
        "purgedcv": "0.1.2",
        "arch": "8.0.0",
    }
    assert card["data"]["feature_cols_n"] == len(card["data"]["feature_cols"])


def test_committed_card_registered_everywhere() -> None:
    """First-class citizen of the freshness map, the API catalog, and as_of."""
    entry = next(
        (e for e in et._DATA_HEALTH_MANIFEST if e[0] == "model_card"), None
    )
    assert entry == ("model_card", "model_card.json", et._DH_FROZEN)
    assert et._API_LICENSE["model_card"] == (
        "Aionis research artifacts (repo PolyForm-NC)",
        "machine-readable model card of the frozen confirmatory Track C model",
    )
    card = _load()
    run_date = card["identity"]["run_ts"].split("T")[0]
    assert et._dh_as_of("model_card", "model_card.json") == run_date
    dh = json.loads((DATA / "data_health.json").read_text(encoding="utf-8"))
    panel = next((p for p in dh["panels"] if p["key"] == "model_card"), None)
    assert panel is not None, "must appear in the committed freshness map"
    assert panel["category"] == "frozen"
    assert panel["as_of"] == run_date
    assert panel["present"] is True
    cat = json.loads((DATA / "api_catalog.json").read_text(encoding="utf-8"))
    ep = next((e for e in cat["endpoints"] if e["key"] == "model_card"), None)
    assert ep is not None and ep["status"] == "available"
    assert ep["freshness"] == "frozen"
    assert ep["license"] == "Aionis research artifacts (repo PolyForm-NC)"
    assert ep["source"] == (
        "machine-readable model card of the frozen confirmatory Track C model"
    )
