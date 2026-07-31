"""E3 Slice 3f - the consolidated forward-commit INVARIANT gate (I4/I6/I7 + cross-checks).

The load-bearing anti-leakage invariants for the forward-commit step, asserted in
one place so a regression is a single-file signal:

  * I4 (no lookahead) - the train block ends >= embargo sessions before the
    predict date on the panel's own date grid; the test cross-section is exactly
    the PIT constituents (NO universe forward-fill to today's 500).
  * I6 (single pinned provider) - exactly ONE provider (glm) is ever used; the
    commit row records provider + provider_cutoff.
  * I7 (end-to-end determinism) - two full freeze -> fit -> commit runs over a
    frozen I_t produce identical scores_sha256; the 2nd commit is idempotent.
  * I1/I2 cross-checks - a committed prediction is reveal-gated; a mutation is
    refused (these are Slice-1's gates, re-asserted here against the runner's output).

I5 (structural-only causal edge) is gated by Pass-A's tests; one cross-check here.
Every fixture is SYNTHETIC and labeled; real LightGBMFrozen on tiny panels.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aionis.eval import forward_commit as FC
from aionis.eval import forward_freeze as FF
from aionis.ingest.forward import _common
from aionis.ingest.forward.earnings_8k_forward import DATASET as EARNINGS_DATASET
from aionis.ingest.forward.macro_forward import DATASET as MACRO_DATASET
from aionis.ingest.forward.stakes_13d_forward import DATASET as STAKES_DATASET
from aionis.ingest.universe import constituents_on, mask_panel_to_pit
from aionis.reporting import forward_ledger as FL
from aionis.schema.causal_edge import FORBIDDEN_FIELDS

PHASE = "E3"
PREDICT_TS = "2026-07-31T20:00:00+00:00"
TARGET_T = "2026-08-31T20:00:00+00:00"


# ---------------------------------------------------------------------------
# SYNTHETIC fixtures (labeled - no real data, no network)
# ---------------------------------------------------------------------------


def _panel(
    n_dates: int = 30, n_tickers: int = 8, seed: int = 0, with_extra: bool = True,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = [d.normalize() for d in pd.bdate_range("2026-01-05", periods=n_dates)]
    tickers = [f"T{i}" for i in range(n_tickers)]
    rows: list[dict] = []
    for d in dates:
        for t in tickers:
            row: dict = {"date": d, "ticker": t, "y_fwd_ret": float(rng.normal(0.0, 0.01))}
            for c in FC.FEATURE_COLS:
                row[c] = float(rng.normal(0.0, 1.0))
            if with_extra:
                for c in FC.FORWARD_EXTRA_COLS:
                    row[c] = float(rng.normal(0.0, 1.0))
            rows.append(row)
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return df.sort_values(["date", "ticker"]).reset_index(drop=True)


def _config(provider: str = "glm", **overrides: object) -> dict:
    cfg: dict = {
        "phase": "E3", "mode": "exploratory", "align_on": "end_lag", "horizon": 21,
        "embargo_sessions": 21,
        "feature_cols_base": list(FC.FEATURE_COLS),
        "feature_cols_e13": list(FC.FEATURE_COLS) + list(FC.FORWARD_EXTRA_COLS),
        "causal_schema_version": "e3-causal-v1",
        "mechanism_keyword_enum": sorted(
            ["earnings_signal", "ownership_change", "guidance", "other"]
        ),
        "ff12_taxonomy": sorted(["NoDur", "Durbl", "Other"]),
        "broadcast_weights": {"version": "bn2017-sign-v1"},
        "frozen_params": {"n_jobs": 1, "random_state": 0},
        "provider": provider, "provider_cutoff": "2026-07-31",
        "versions": {"lightgbm": "x"}, "iset_sha256": "i" * 64, "uv_lock_sha256": "u" * 64,
    }
    cfg.update(overrides)
    return cfg


def _ledger_rows(runs_dir: Path) -> list[dict]:
    ledger = runs_dir / "ledger.jsonl"
    if not ledger.exists():
        return []
    return [json.loads(ln) for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]


# ---------------------------------------------------------------------------
# I4 - no lookahead in the train block
# ---------------------------------------------------------------------------


def test_invariant_I4_no_lookahead_in_train_block() -> None:
    """The train block's max date is >= embargo sessions before the predict date (grid-indexed)."""
    panel = _panel(n_dates=30, n_tickers=8)
    predict_date = panel["date"].max()
    train, test = FC.pit_train_test_split(panel, predict_date, embargo_sessions=21)
    dates_sorted = pd.DatetimeIndex(sorted(panel["date"].unique()))
    pos = {d: i for i, d in enumerate(dates_sorted)}
    # the embargo gap is a whole-sessions gap on the panel's OWN grid
    assert pos[train["date"].max()] <= pos[predict_date] - 21
    # train and test share NO date (no leaked predict-date row in train)
    assert not (set(train["date"]) & set(test["date"]))


def test_invariant_I4_no_universe_forward_fill() -> None:
    """The test cross-section is EXACTLY the PIT constituents (no forward-fill to today's 500)."""
    panel = _panel(n_dates=30, n_tickers=8)
    predict_date = panel["date"].max()
    dates_sorted = pd.DatetimeIndex(sorted(panel["date"].unique()))
    # membership: all 8 tickers at the start; only T0..T4 in the latest pre-predict snapshot
    early = pd.DataFrame(
        [{"date": dates_sorted[0], "ticker": t} for t in [f"T{i}" for i in range(8)]]
    )
    late = pd.DataFrame(
        [{"date": dates_sorted[28], "ticker": t} for t in [f"T{i}" for i in range(5)]]
    )
    membership = pd.concat([early, late], ignore_index=True)
    membership["date"] = pd.to_datetime(membership["date"]).dt.normalize()

    pit = constituents_on(membership, predict_date)
    assert pit == {f"T{i}" for i in range(5)}  # the latest snapshot <= predict_date

    masked = mask_panel_to_pit(panel, membership)  # the deferred PIT mask
    _train, test = FC.pit_train_test_split(masked, predict_date, embargo_sessions=21,
                                           membership=membership)
    # the test cross-section equals the PIT constituents exactly - T5/T6/T7 were dropped,
    # and NO ticker beyond the PIT set was fabricated (no forward-fill)
    assert set(test["ticker"]) == pit
    assert {f"T{i}" for i in (5, 6, 7)}.isdisjoint(set(test["ticker"]))


# ---------------------------------------------------------------------------
# I6 - single pinned provider
# ---------------------------------------------------------------------------


def test_invariant_I6_single_pinned_provider_glm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only the glm provider is ever selected even when others are enabled."""

    class _P:
        def __init__(self, name: str) -> None:
            self.name = name

    # glm is priority-1; siliconflow/modelscope present but MUST NOT be picked
    monkeypatch.setattr(
        FC, "build_providers",
        lambda only_enabled=True: [_P("siliconflow"), _P("glm"), _P("modelscope")],
    )
    p = FC.resolve_pinned_provider("glm")
    assert p.name == "glm"  # exactly glm, never a fallback


def test_invariant_I6_commit_row_records_provider_and_cutoff(tmp_path: Path) -> None:
    """The committed ledger row records provider=glm + provider_cutoff (I6 audit trail)."""
    panel_base = _panel(with_extra=False)
    panel_e13 = _panel(with_extra=True)
    FC.run_forward_commit(
        predict_ts=PREDICT_TS, target_t=TARGET_T,
        panel_base=panel_base, panel_e13=panel_e13, config=_config(),
        iset_sha256="i" * 64, provider="glm", provider_cutoff="2026-07-31",
        runs_dir=tmp_path,
    )
    commits = [
        r for r in _ledger_rows(tmp_path)
        if r.get("event") == "forward_prediction_committed"
    ]
    assert len(commits) == 1
    assert commits[0]["provider"] == "glm"
    assert commits[0]["provider_cutoff"] == "2026-07-31"


# ---------------------------------------------------------------------------
# I7 - end-to-end determinism (two full freeze -> fit -> commit runs)
# ---------------------------------------------------------------------------


def _patch_deterministic_freeze(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock the three collectors to DETERMINISTIC frames + sealed archives (frozen I_t)."""

    def _archive(cache_dir, dataset, snapshot_ts, frame):
        cdir = _common.cache_dir(cache_dir)
        snap = _common.canonical_snapshot_ts(snapshot_ts)
        _common.archive_raw(cdir, dataset, snap, frame.to_dict("records"))
        return frame

    macro = pd.DataFrame([
        {"series_id": "CPIAUCSL", "event_type": "CPI", "pub_date": "2026-07-15",
         "surprise_z": 0.3, "value": 0.3, "event_ts": "2026-07-15",
         "snapshot_ts": PREDICT_TS, "feature": "m", "ref_date": "2026-07-15"},
    ])
    stakes = pd.DataFrame([
        {"ticker": "T0", "cik": 1, "feature": "stake_13d_filing", "value": 1.0,
         "form": "SC 13D", "filing_date": "2026-07-10", "accession": "0001",
         "event_ts": "2026-07-10", "snapshot_ts": PREDICT_TS},
    ])
    earnings = pd.DataFrame([
        {"ticker": "T0", "cik": 1, "feature": "earnings_8k_item_2_02", "value": 1.0,
         "form": "8-K", "filing_date": "2026-07-12", "accession": "0003",
         "items": "Item 2.02", "event_ts": "2026-07-12", "snapshot_ts": PREDICT_TS},
    ])

    monkeypatch.setattr(
        FF, "collect_macro_forward",
        lambda *, snapshot_ts, last_poll_ts, fred_api_key, cache_dir, runs_dir:
        _archive(cache_dir, MACRO_DATASET, snapshot_ts, macro.copy()),
    )
    monkeypatch.setattr(
        FF, "collect_13d_forward",
        lambda ciks, *, snapshot_ts, last_poll_ts, cache_dir, runs_dir:
        _archive(cache_dir, STAKES_DATASET, snapshot_ts, stakes.copy()),
    )
    monkeypatch.setattr(
        FF, "collect_8k_forward",
        lambda tickers, *, snapshot_ts, last_poll_ts, cache_dir, runs_dir:
        _archive(cache_dir, EARNINGS_DATASET, snapshot_ts, earnings.copy()),
    )


def test_invariant_I7_end_to_end_determinism(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two full freeze -> fit -> commit runs over a frozen I_t -> identical scores_sha256."""
    _patch_deterministic_freeze(monkeypatch)
    cache = tmp_path / "cache"
    panel_base = _panel(with_extra=False)
    panel_e13 = _panel(with_extra=True)

    # run 1: freeze -> manifest -> config -> commit
    out1 = FF.freeze_forward_iset(
        snapshot_ts=PREDICT_TS, last_poll_ts="2026-06-30T20:00:00+00:00",
        ciks={"T0": 1}, tickers=[f"T{i}" for i in range(8)],
        fred_api_key="k", cache_dir=cache, runs_dir=tmp_path,
    )
    manifest1 = FF.iset_manifest(out1, uv_lock_sha256="u" * 64)
    iset_sha1 = FF.iset_sha256_from_manifest(manifest1)
    r1 = FC.run_forward_commit(
        predict_ts=PREDICT_TS, target_t=TARGET_T, panel_base=panel_base,
        panel_e13=panel_e13, config=_config(iset_sha256=iset_sha1),
        iset_sha256=iset_sha1, provider="glm", provider_cutoff="2026-07-31",
        runs_dir=tmp_path,
    )

    # run 2: same freeze (idempotent archive) -> same manifest -> same commit (idempotent)
    out2 = FF.freeze_forward_iset(
        snapshot_ts=PREDICT_TS, last_poll_ts="2026-06-30T20:00:00+00:00",
        ciks={"T0": 1}, tickers=[f"T{i}" for i in range(8)],
        fred_api_key="k", cache_dir=cache, runs_dir=tmp_path,
    )
    manifest2 = FF.iset_manifest(out2, uv_lock_sha256="u" * 64)
    iset_sha2 = FF.iset_sha256_from_manifest(manifest2)
    r2 = FC.run_forward_commit(
        predict_ts=PREDICT_TS, target_t=TARGET_T, panel_base=panel_base.copy(),
        panel_e13=panel_e13.copy(), config=_config(iset_sha256=iset_sha2),
        iset_sha256=iset_sha2, provider="glm", provider_cutoff="2026-07-31",
        runs_dir=tmp_path,
    )

    # frozen I_t -> identical iset_sha256; deterministic fit -> identical scores_sha256
    assert iset_sha1 == iset_sha2
    assert r1["scores_sha256"] == r2["scores_sha256"]
    # the second commit was idempotent (no duplicate)
    assert r1.get("_appended") is True
    assert r2.get("_appended") is False
    commits = [
        r for r in _ledger_rows(tmp_path)
        if r.get("event") == "forward_prediction_committed"
    ]
    assert len(commits) == 1


# ---------------------------------------------------------------------------
# I1 cross-check - a committed prediction is reveal-gated (before target_t)
# ---------------------------------------------------------------------------


def test_cross_check_I1_committed_prediction_is_reveal_gated(tmp_path: Path) -> None:
    """A committed forward prediction cannot be revealed before its target_t (I1)."""
    panel_base = _panel(with_extra=False)
    panel_e13 = _panel(with_extra=True)
    res = FC.run_forward_commit(
        predict_ts=PREDICT_TS, target_t=TARGET_T,
        panel_base=panel_base, panel_e13=panel_e13, config=_config(),
        iset_sha256="i" * 64, provider="glm", provider_cutoff="2026-07-31",
        runs_dir=tmp_path,
    )
    csha = res["config_sha256"]
    # a reveal BEFORE target_t is refused (no scored row appended)
    reveal = FL.reveal_forward_outcome(
        TARGET_T, 0.03, "arm_e13", predict_ts=PREDICT_TS, config_sha256=csha,
        runs_dir=tmp_path, now="2026-07-31T20:00:00+00:00",  # < target_t
    )
    assert reveal["revealed"] is False
    scored = [r for r in _ledger_rows(tmp_path) if r.get("event") == "forward_outcome_scored"]
    assert scored == []


# ---------------------------------------------------------------------------
# I2 cross-check - a mutation of sealed scores is refused
# ---------------------------------------------------------------------------


def test_cross_check_I2_mutation_of_sealed_scores_refused(tmp_path: Path) -> None:
    """Re-committing the SAME predict_ts with MUTATED scores is refused (I2)."""
    panel_base = _panel(with_extra=False, seed=1)
    panel_e13 = _panel(with_extra=True, seed=1)
    first = FC.run_forward_commit(
        predict_ts=PREDICT_TS, target_t=TARGET_T,
        panel_base=panel_base, panel_e13=panel_e13, config=_config(),
        iset_sha256="i" * 64, provider="glm", provider_cutoff="2026-07-31",
        runs_dir=tmp_path,
    )
    # a DIFFERENT panel (seed=2) -> different scores -> mutation of the sealed predict_ts
    mut_base = _panel(with_extra=False, seed=2)
    mut_e13 = _panel(with_extra=True, seed=2)
    refused = FC.run_forward_commit(
        predict_ts=PREDICT_TS, target_t=TARGET_T,
        panel_base=mut_base, panel_e13=mut_e13, config=_config(),
        iset_sha256="i" * 64, provider="glm", provider_cutoff="2026-07-31",
        runs_dir=tmp_path,
    )
    # the second commit's mutated scores are refused (not silently overwritten)
    assert first["scores_sha256"] != refused["scores_sha256"]
    commits = [
        r for r in _ledger_rows(tmp_path)
        if r.get("event") == "forward_prediction_committed"
        and r.get("predict_ts") == PREDICT_TS
    ]
    assert len(commits) == 1  # the original sealed row only


# ---------------------------------------------------------------------------
# I5 cross-check - the causal edge rejects outcome fields (Pass-A boundary)
# ---------------------------------------------------------------------------


def test_cross_check_I5_causal_edge_rejects_outcome_fields() -> None:
    """The forward causal edge rejects every I5 forbidden outcome field (no leakage)."""
    from aionis.schema.causal_edge import assert_no_forbidden

    for field in FORBIDDEN_FIELDS:
        with pytest.raises(ValueError, match="I5 leakage"):
            assert_no_forbidden({field: "anything"})
