"""E3 Slice 3d - the forward-commit step core (fit-on-I_t -> commit).

TDD: these tests FAIL until ``src/aionis/eval/forward_commit.py`` exists and:
  * PIT-splits the panel so the train block has NO lookahead (I4) and the test
    cross-section is exactly the predict-date PIT constituents (no forward-fill);
  * fits a SINGLE LightGBMFrozen per arm (one fit_predict, no CV) -> deterministic
    bit-identical scores on a re-run (I7);
  * builds a frozen config whose sha256 flips on provider / causal-schema /
    mechanism-enum change (I6/I8) and records provider + provider_cutoff;
  * runs the freeze -> config -> fit -> commit ORDER (I1: config sealed BEFORE any
    score exists; commit only after fit);
  * emits the LONG [ticker, arm, score] panel both arms; refuses non-glm; and
    supports ``no_ledger=True`` (computes the sig without writing).

Every fixture is SYNTHETIC and labeled; real LightGBMFrozen runs on tiny fixtures
(determinism is its own H6 contract). No network.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aionis.eval import forward_commit as FC
from aionis.eval.learner import LightGBMFrozen
from aionis.reporting import forward_ledger as FL

PHASE = "E3"
PREDICT_TS = "2026-07-31T20:00:00+00:00"
TARGET_T = "2026-08-31T20:00:00+00:00"


# ---------------------------------------------------------------------------
# SYNTHETIC panel fixtures (labeled - no real data)
# ---------------------------------------------------------------------------


def _dates(n: int = 30) -> list[pd.Timestamp]:
    """n deterministic business-day sessions (predict_date = the last)."""
    return [d.normalize() for d in pd.bdate_range("2026-01-05", periods=n)]


def _panel(
    n_dates: int = 30, n_tickers: int = 8, seed: int = 0, with_extra: bool = False,
) -> pd.DataFrame:
    """SYNTHETIC PIT panel [date, ticker, y_fwd_ret, FEATURE_COLS[, FORWARD_EXTRA_COLS]]."""
    rng = np.random.default_rng(seed)
    dates = _dates(n_dates)
    tickers = [f"T{i}" for i in range(n_tickers)]
    rows: list[dict] = []
    for d in dates:
        for t in tickers:
            row: dict = {"date": d, "ticker": t, "y_fwd_ret": float(rng.normal(0.0, 0.01))}
            for c in FC.FEATURE_COLS:
                row[c] = float(rng.normal(0.0, 1.0)) if rng.random() > 0.05 else float("nan")
            if with_extra:
                for c in FC.FORWARD_EXTRA_COLS:
                    row[c] = float(rng.normal(0.0, 1.0)) if rng.random() > 0.10 else float("nan")
            rows.append(row)
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return df.sort_values(["date", "ticker"]).reset_index(drop=True)


def _base_config(provider: str = "glm", **overrides: object) -> dict:
    """A minimal frozen-config stub with all build_forward_config fields."""
    cfg: dict = {
        "phase": "E3",
        "mode": "exploratory",
        "align_on": "end_lag",
        "horizon": 21,
        "embargo_sessions": 21,
        "feature_cols_base": list(FC.FEATURE_COLS),
        "feature_cols_e13": list(FC.FEATURE_COLS) + list(FC.FORWARD_EXTRA_COLS),
        "causal_schema_version": "e3-causal-v1",
        "mechanism_keyword_enum": sorted(
            ["earnings_signal", "ownership_change", "guidance", "other"]
        ),
        "ff12_taxonomy": sorted(["NoDur", "Durbl", "Manuf", "Enrgy", "Chems", "BusEq",
                                 "Telcm", "Utils", "Shops", "Hlth", "Money", "Other"]),
        "broadcast_weights": {"version": "bn2017-sign-v1", "status": "exploratory-v1-qualitative"},
        "frozen_params": {"n_jobs": 1, "random_state": 0},
        "provider": provider,
        "provider_cutoff": "2026-07-31",
        "versions": {"lightgbm": "x"},
        "iset_sha256": "i" * 64,
        "uv_lock_sha256": "u" * 64,
    }
    cfg.update(overrides)
    return cfg


def _ledger_rows(runs_dir: Path) -> list[dict]:
    ledger = runs_dir / "ledger.jsonl"
    if not ledger.exists():
        return []
    return [json.loads(ln) for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]


# ---------------------------------------------------------------------------
# I4 - PIT train/test split excludes lookahead
# ---------------------------------------------------------------------------


def test_pit_split_excludes_lookahead_from_train_block() -> None:
    """I4: train block ends >= embargo sessions before predict_date (no lookahead)."""
    panel = _panel(n_dates=30, n_tickers=8)
    predict_date = panel["date"].max()
    train, test = FC.pit_train_test_split(panel, predict_date, embargo_sessions=21)
    dates_sorted = pd.DatetimeIndex(sorted(panel["date"].unique()))
    pos = {d: i for i, d in enumerate(dates_sorted)}
    # train max is at least embargo sessions before predict_date on the grid
    assert pos[train["date"].max()] <= pos[predict_date] - 21
    # test is EXACTLY the predict-date cross-section
    assert set(test["date"]) == {predict_date}
    assert len(test) == 8
    # and train/test are disjoint in date
    assert not set(train["date"]) & set(test["date"])


def test_pit_split_predict_date_not_in_grid_yields_empty_test() -> None:
    """I4: a predict_date absent from the panel yields an empty test (no fabrication)."""
    panel = _panel(n_dates=30, n_tickers=8)
    predict_date = panel["date"].max() + pd.Timedelta(days=30)  # not a grid date
    train, test = FC.pit_train_test_split(panel, predict_date, embargo_sessions=21)
    assert len(test) == 0  # no forward-fill of an unknown session


# ---------------------------------------------------------------------------
# single fit - one fit_predict per arm, no CV
# ---------------------------------------------------------------------------


def test_fit_forward_single_calls_fit_predict_once(tmp_path: Path) -> None:
    """No CV: fit_forward_single performs exactly ONE fit_predict (the frozen single fit)."""
    panel = _panel(n_dates=30, n_tickers=8, with_extra=True)
    predict_date = panel["date"].max()
    calls = {"n": 0}
    orig = LightGBMFrozen.fit_predict

    def _spy(self, train, test, feature_cols, y_col):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return orig(self, train, test, feature_cols, y_col)

    monkey = pytest.MonkeyPatch()
    monkey.setattr(LightGBMFrozen, "fit_predict", _spy)
    try:
        FC.fit_forward_single(panel, predict_date, FC.FEATURE_COLS + FC.FORWARD_EXTRA_COLS)
    finally:
        monkey.undo()
    assert calls["n"] == 1  # single fit, no CV


# ---------------------------------------------------------------------------
# I7 - determinism (bit-identical scores on a re-run)
# ---------------------------------------------------------------------------


def test_fit_forward_single_is_deterministic() -> None:
    """I7: two fits on the identical panel produce bit-identical scores."""
    panel = _panel(n_dates=30, n_tickers=8, with_extra=True, seed=0)
    predict_date = panel["date"].max()
    s1 = FC.fit_forward_single(panel, predict_date, FC.FEATURE_COLS + FC.FORWARD_EXTRA_COLS)
    s2 = FC.fit_forward_single(panel.copy(), predict_date, FC.FEATURE_COLS + FC.FORWARD_EXTRA_COLS)
    np.testing.assert_array_equal(s1.to_numpy(), s2.to_numpy())


# ---------------------------------------------------------------------------
# config_sha256 flips on provider / schema / mechanism change (I6/I8)
# ---------------------------------------------------------------------------


def test_config_sha256_flips_on_provider_change() -> None:
    """I6/I8: provider glm vs siliconflow -> different config_sha256 (new sequence)."""
    a = FL.config_sha256(_base_config(provider="glm"))
    b = FL.config_sha256(_base_config(provider="siliconflow"))
    assert a != b


def test_config_sha256_flips_on_schema_version_bump() -> None:
    """I8: causal_schema_version bump -> different config_sha256."""
    a = FL.config_sha256(_base_config(causal_schema_version="e3-causal-v1"))
    b = FL.config_sha256(_base_config(causal_schema_version="e3-causal-v2"))
    assert a != b


def test_config_sha256_flips_on_mechanism_enum_change() -> None:
    """I8: adding a mechanism keyword -> different config_sha256."""
    base = sorted(["earnings_signal", "ownership_change", "guidance", "other"])
    grown = sorted(base + ["new_keyword"])
    a = FL.config_sha256(_base_config(mechanism_keyword_enum=base))
    b = FL.config_sha256(_base_config(mechanism_keyword_enum=grown))
    assert a != b


def test_frozen_beta_sha256_is_stable_64hex_and_content_sensitive() -> None:
    """I8 (FIX1): FROZEN_BETA_SHA256 is a 64-hex CONTENT hash; a sign flip changes it."""
    import hashlib as _hl

    from aionis.features.frozen_beta import FROZEN_BETA, FROZEN_BETA_SHA256

    assert isinstance(FROZEN_BETA_SHA256, str) and len(FROZEN_BETA_SHA256) == 64

    def _content_hash(table: dict) -> str:
        return _hl.sha256(
            json.dumps(
                sorted(((s.value, sh, v) for (s, sh), v in table.items())),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

    # bit-stable: recompute from the literal -> identical (H6)
    assert _content_hash(FROZEN_BETA) == FROZEN_BETA_SHA256
    # content-sensitive: flip one sign -> different hash (closes the silent-mutation hole)
    flipped = dict(FROZEN_BETA)
    k0 = next(iter(flipped))
    flipped[k0] = -flipped[k0]
    assert _content_hash(flipped) != FROZEN_BETA_SHA256


def test_config_sha256_flips_on_frozen_beta_sign_change() -> None:
    """I8 (FIX1): differing frozen_beta_sha256 (sign CONTENT) -> different config_sha256."""
    from aionis.features.frozen_beta import FROZEN_BETA_SHA256

    common: dict = dict(
        horizon=21,
        shas={"iset_sha256": "i" * 64, "uv_lock_sha256": "u" * 64},
        versions={"lightgbm": "x"},
        provider="glm",
        provider_cutoff="2026-07-31",
        causal_schema_version="e3-causal-v1",
        mechanism_keyword_enum=["earnings_signal", "ownership_change", "guidance", "other"],
        ff12_taxonomy=["NoDur", "Durbl", "Other"],
        broadcast_weights={"version": "bn2017-sign-v1"},
        frozen_params={},
    )
    cfg_real = FC.build_forward_config(frozen_beta_sha256=FROZEN_BETA_SHA256, **common)
    cfg_flipped = FC.build_forward_config(frozen_beta_sha256="z" * 64, **common)
    # the content hash is in the built config
    assert cfg_real["frozen_beta_sha256"] == FROZEN_BETA_SHA256
    assert cfg_real["frozen_beta_sha256"] != cfg_flipped["frozen_beta_sha256"]
    # a sign-content change flips the sequence key
    assert FL.config_sha256(cfg_real) != FL.config_sha256(cfg_flipped)


def test_config_sha256_flips_on_frozen_params_change() -> None:
    """I8 (FIX2): a frozen-learner hyperparameter override -> different config_sha256."""
    from aionis.eval.learner import FROZEN_PARAMS

    common: dict = dict(
        horizon=21,
        shas={"iset_sha256": "i" * 64, "uv_lock_sha256": "u" * 64},
        versions={"lightgbm": "x"},
        provider="glm",
        provider_cutoff="2026-07-31",
        causal_schema_version="e3-causal-v1",
        mechanism_keyword_enum=["earnings_signal", "ownership_change", "guidance", "other"],
        ff12_taxonomy=["NoDur", "Durbl", "Other"],
        broadcast_weights={"version": "bn2017-sign-v1"},
        frozen_beta_sha256="a" * 64,
    )
    cfg_base = FC.build_forward_config(frozen_params={}, **common)
    cfg_override = FC.build_forward_config(frozen_params={"n_estimators": 99999}, **common)
    # the FULL canonical FROZEN_PARAMS is in the config (not a 2-key caller subset)
    assert set(FROZEN_PARAMS.keys()).issubset(set(cfg_base["frozen_params"].keys()))
    # a hyperparameter override flips the sequence key
    assert FL.config_sha256(cfg_base) != FL.config_sha256(cfg_override)


def test_build_forward_config_has_e3_schema_fields() -> None:
    """build_forward_config emits phase/mode/align_on + both feature-col lists + all shas."""
    cfg = FC.build_forward_config(
        horizon=21,
        shas={"iset_sha256": "i" * 64, "uv_lock_sha256": "u" * 64, "prices_sha256": "p" * 64},
        versions={"lightgbm": "4.3"},
        provider="glm",
        provider_cutoff="2026-07-31",
        causal_schema_version="e3-causal-v1",
        mechanism_keyword_enum=["ownership_change", "earnings_signal", "guidance", "other"],
        ff12_taxonomy=["NoDur", "Durbl", "Other"],
        broadcast_weights={"version": "bn2017-sign-v1"},
        frozen_params={"n_jobs": 1, "random_state": 0},
    )
    assert cfg["phase"] == "E3"
    assert cfg["mode"] == "exploratory"
    assert cfg["align_on"] == "end_lag"
    assert cfg["feature_cols_base"] == list(FC.FEATURE_COLS)
    assert cfg["feature_cols_e13"] == list(FC.FEATURE_COLS) + list(FC.FORWARD_EXTRA_COLS)
    assert cfg["causal_schema_version"] == "e3-causal-v1"
    # mechanism enum is sorted in the config (deterministic)
    assert cfg["mechanism_keyword_enum"] == sorted(cfg["mechanism_keyword_enum"])
    assert cfg["ff12_taxonomy"] == sorted(cfg["ff12_taxonomy"])
    assert cfg["provider"] == "glm"
    assert cfg["provider_cutoff"] == "2026-07-31"
    assert cfg["iset_sha256"] == "i" * 64
    assert cfg["prices_sha256"] == "p" * 64


# ---------------------------------------------------------------------------
# run_forward_commit - ordering (I1), long shape, provider recorded, refuses
# ---------------------------------------------------------------------------


def test_run_forward_commit_order_config_before_fit_before_commit(tmp_path: Path) -> None:
    """I1: config_sha256 is sealed BEFORE any fit, and fit BEFORE commit."""
    panel_base = _panel(n_dates=30, n_tickers=8, seed=0)
    panel_e13 = _panel(n_dates=30, n_tickers=8, seed=0, with_extra=True)
    cfg = _base_config()
    log: list[tuple[int, str]] = []
    counter = {"n": 0}

    def _tick(name: str) -> None:
        counter["n"] += 1
        log.append((counter["n"], name))

    orig_csha = FL.config_sha256
    orig_commit = FL.commit_forward_prediction
    orig_fit = LightGBMFrozen.fit_predict

    def _csha_spy(config):  # type: ignore[no-untyped-def]
        _tick("config_sha256")
        return orig_csha(config)

    def _commit_spy(*a, **k):  # type: ignore[no-untyped-def]
        _tick("commit")
        return orig_commit(*a, **k)

    def _fit_spy(self, train, test, feature_cols, y_col):  # type: ignore[no-untyped-def]
        _tick("fit")
        return orig_fit(self, train, test, feature_cols, y_col)

    monkey = pytest.MonkeyPatch()
    monkey.setattr(FL, "config_sha256", _csha_spy)
    monkey.setattr(FL, "commit_forward_prediction", _commit_spy)
    monkey.setattr(LightGBMFrozen, "fit_predict", _fit_spy)
    try:
        FC.run_forward_commit(
            predict_ts=PREDICT_TS, target_t=TARGET_T,
            panel_base=panel_base, panel_e13=panel_e13, config=cfg,
            iset_sha256="i" * 64, provider="glm", provider_cutoff="2026-07-31",
            runs_dir=tmp_path,
        )
    finally:
        monkey.undo()
    names_in_order = [name for _, name in log]
    # the FIRST event is config_sha256 (sealed before any fit); first fit precedes commit
    assert names_in_order[0] == "config_sha256"
    first_fit = names_in_order.index("fit")
    first_commit = names_in_order.index("commit")
    assert first_fit < first_commit
    # config sealed before the first fit
    assert names_in_order.index("config_sha256") < first_fit


def test_run_forward_commit_emits_long_scores_both_arms(tmp_path: Path) -> None:
    """The committed scores parquet carries BOTH arms over the predict-date cross-section."""
    panel_base = _panel(n_dates=30, n_tickers=8, seed=0)
    panel_e13 = _panel(n_dates=30, n_tickers=8, seed=0, with_extra=True)
    res = FC.run_forward_commit(
        predict_ts=PREDICT_TS, target_t=TARGET_T,
        panel_base=panel_base, panel_e13=panel_e13, config=_base_config(),
        iset_sha256="i" * 64, provider="glm", provider_cutoff="2026-07-31",
        runs_dir=tmp_path,
    )
    assert res["committed"] is True
    csha = res["config_sha256"]
    parquet = tmp_path / "forward" / csha / "scores_20260731T2000000000.parquet"
    assert parquet.exists()
    df = pd.read_parquet(parquet)
    assert set(df["arm"]) == {"arm_base", "arm_e13"}
    assert set(df.columns) == {"ticker", "arm", "score"}
    # 8 tickers x 2 arms
    assert len(df) == 16


def test_run_forward_commit_records_provider_and_cutoff(tmp_path: Path) -> None:
    """I6: the commit row records provider + provider_cutoff."""
    panel_base = _panel(n_dates=30, n_tickers=8, seed=0)
    panel_e13 = _panel(n_dates=30, n_tickers=8, seed=0, with_extra=True)
    FC.run_forward_commit(
        predict_ts=PREDICT_TS, target_t=TARGET_T,
        panel_base=panel_base, panel_e13=panel_e13, config=_base_config(),
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
    assert commits[0]["phase"] == PHASE


def test_run_forward_commit_refuses_non_glm_provider(tmp_path: Path) -> None:
    """I6: a non-glm provider is refused (no commit, no fit)."""
    panel_base = _panel(n_dates=30, n_tickers=8, seed=0)
    panel_e13 = _panel(n_dates=30, n_tickers=8, seed=0, with_extra=True)
    with pytest.raises(ValueError, match="glm"):
        FC.run_forward_commit(
            predict_ts=PREDICT_TS, target_t=TARGET_T,
            panel_base=panel_base, panel_e13=panel_e13, config=_base_config(provider="siliconflow"),
            iset_sha256="i" * 64, provider="siliconflow", provider_cutoff="2026-07-31",
            runs_dir=tmp_path,
        )
    # no commit row, no parquet
    assert _ledger_rows(tmp_path) == []
    assert not (tmp_path / "forward").exists()


def test_run_forward_commit_no_ledger_computes_sig_without_writing(tmp_path: Path) -> None:
    """no_ledger=True: 0 ledger rows but the scores sig is still computed."""
    panel_base = _panel(n_dates=30, n_tickers=8, seed=0)
    panel_e13 = _panel(n_dates=30, n_tickers=8, seed=0, with_extra=True)
    res = FC.run_forward_commit(
        predict_ts=PREDICT_TS, target_t=TARGET_T,
        panel_base=panel_base, panel_e13=panel_e13, config=_base_config(),
        iset_sha256="i" * 64, provider="glm", provider_cutoff="2026-07-31",
        runs_dir=tmp_path, no_ledger=True,
    )
    assert res["committed"] is False
    assert len(res["scores_sha256"]) == 64  # sig computed
    assert _ledger_rows(tmp_path) == []     # nothing written
    assert not (tmp_path / "forward").exists()


def test_run_forward_commit_is_deterministic_and_idempotent(tmp_path: Path) -> None:
    """I7: a second full run yields identical scores_sha256 and an idempotent commit."""
    panel_base = _panel(n_dates=30, n_tickers=8, seed=0)
    panel_e13 = _panel(n_dates=30, n_tickers=8, seed=0, with_extra=True)
    cfg = _base_config()
    r1 = FC.run_forward_commit(
        predict_ts=PREDICT_TS, target_t=TARGET_T, panel_base=panel_base, panel_e13=panel_e13,
        config=cfg, iset_sha256="i" * 64, provider="glm", provider_cutoff="2026-07-31",
        runs_dir=tmp_path,
    )
    r2 = FC.run_forward_commit(
        predict_ts=PREDICT_TS, target_t=TARGET_T, panel_base=panel_base.copy(),
        panel_e13=panel_e13.copy(), config=cfg, iset_sha256="i" * 64,
        provider="glm", provider_cutoff="2026-07-31", runs_dir=tmp_path,
    )
    assert r1["scores_sha256"] == r2["scores_sha256"]
    assert r1.get("_appended") is True   # first commit appended
    assert r2.get("_appended") is False  # second was idempotent
    commits = [
        r for r in _ledger_rows(tmp_path)
        if r.get("event") == "forward_prediction_committed"
    ]
    assert len(commits) == 1             # no duplicate


def test_no_ledger_sig_equals_live_sig(tmp_path: Path) -> None:
    """FIX5: the no_ledger dry-run scores_sha256 == the live commit's scores_sha256.

    Faithfulness check: the dry-run path must report the SAME sig a real commit
    would seal (it uses the same ``_normalize_scores`` / ``_deterministic_parquet_bytes``
    helpers as ``commit_forward_prediction``), so an operator can trust ``no_ledger``
    output for pre-flight sig checks.
    """
    panel_base = _panel(n_dates=30, n_tickers=8, seed=0)
    panel_e13 = _panel(n_dates=30, n_tickers=8, seed=0, with_extra=True)
    cfg = _base_config()
    live = FC.run_forward_commit(
        predict_ts=PREDICT_TS, target_t=TARGET_T, panel_base=panel_base, panel_e13=panel_e13,
        config=cfg, iset_sha256="i" * 64, provider="glm", provider_cutoff="2026-07-31",
        runs_dir=tmp_path,
    )
    dry = FC.run_forward_commit(
        predict_ts=PREDICT_TS, target_t=TARGET_T, panel_base=panel_base.copy(),
        panel_e13=panel_e13.copy(), config=cfg, iset_sha256="i" * 64,
        provider="glm", provider_cutoff="2026-07-31", runs_dir=tmp_path, no_ledger=True,
    )
    assert live["committed"] is True
    assert dry["committed"] is False
    assert len(live["scores_sha256"]) == 64 and len(dry["scores_sha256"]) == 64
    assert live["scores_sha256"] == dry["scores_sha256"]  # dry-run is faithful to live


# ---------------------------------------------------------------------------
# resolve_pinned_provider (I6 - single pinned provider)
# ---------------------------------------------------------------------------


def test_resolve_pinned_provider_returns_glm(monkeypatch: pytest.MonkeyPatch) -> None:
    """I6: resolve_pinned_provider returns the enabled glm Provider."""

    class _P:
        name = "glm"

    monkeypatch.setattr(FC, "build_providers", lambda only_enabled=True: [_P()])
    p = FC.resolve_pinned_provider("glm")
    assert p.name == "glm"


def test_resolve_pinned_provider_raises_when_glm_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """I6: with no enabled glm provider, resolve raises (never silently falls back)."""

    class _P:
        name = "siliconflow"

    monkeypatch.setattr(FC, "build_providers", lambda only_enabled=True: [_P()])
    with pytest.raises(RuntimeError, match="glm"):
        FC.resolve_pinned_provider("glm")
