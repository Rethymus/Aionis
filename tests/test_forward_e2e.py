"""E3 Slice 7 - hermetic E2E smoke chain + the E2E-owned I1/I2/I9 gates.

Runs the FULL forward pipeline on labeled synthetic fixtures in ``tmp_path``:
  COMMIT (Slice 3d: fit-on-I_t -> sha256-seal) -> FAST-FORWARD 21 sessions ->
  REVEAL + SCORE (Slice 4b) -> ACCUMULATE (Slice 4c) -> I9 separation check.

Every fixture is SYNTHETIC and labeled (no real data, no network, no real model
calls beyond the frozen LightGBM on tiny fixtures, which is its own H6 contract).

I1-I9 coverage map - what THIS suite adds vs what other suites already own:
  * I1 (commit-before-reveal): the chain reveals with now < target_t and asserts
    both arms are refused with reason ``before_target_t`` (this file). The seal
    ORDER (config_sha256 before fit before commit) is owned by
    ``test_forward_commit_core.py::test_run_forward_commit_order_config_before_fit_before_commit``.
  * I2 (immutability + idempotency): byte-stable scores-parquet re-reads and a
    byte-mutation hash flip (``test_e2e_scores_parquet_immutable_sha256``) plus a
    double-reveal that appends no duplicate scored rows (chain, this file). The
    deeper ledger invariants are owned by ``test_forward_ledger_invariants.py``.
  * I3 (forward-only ingest): owned by ``test_forward_ingest.py`` - NOT duplicated.
  * I4 (no-lookahead PIT split): owned by ``test_forward_commit_invariants.py``
    and ``test_forward_commit_core.py`` - NOT duplicated.
  * I5 (structural-only ERL / no market impact): owned by the ERL suites - NOT duplicated.
  * I6 (single pinned glm provider): owned by ``test_forward_commit_core.py`` - NOT duplicated.
  * I7 (determinism / bit-identical re-runs): owned by ``test_forward_commit_core.py``
    and ``test_forward_score.py`` - NOT duplicated.
  * I8 (headline isolation / config-sha keying): owned by
    ``test_forward_commit_core.py`` - NOT duplicated.
  * I9 (forward ledger vs confirmatory ledger separation): the chain asserts the
    E2E wrote ONLY ``runs/forward/`` + ``runs/ledger.jsonl`` and NEVER
    ``runs/results/`` (this file).

No writes ever touch the real ``runs/ledger.jsonl`` - the runs dir is
``tmp_path``-only (guarded independently by
``test_forward_commit_runner.py::test_real_ledger_jsonl_untouched``).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from aionis.eval import forward_commit as FC
from aionis.eval import forward_score as FS
from aionis.reporting import forward_ledger as FL

PHASE = "E3"
# NYSE month-end session closes at 20:00 UTC (2026-07-31 = Fri, 2026-08-31 = Mon).
PREDICT_TS = "2026-07-31T20:00:00+00:00"
TARGET_T = "2026-08-31T20:00:00+00:00"
NOW_BEFORE = "2026-08-15T00:00:00+00:00"   # < target_t (I1 gate fires)
NOW_AFTER = "2026-08-31T21:00:00+00:00"    # >= target_t (outcome realized)


# ---------------------------------------------------------------------------
# SYNTHETIC fixtures (shapes reused from test_forward_commit_core.py - canonical)
# ---------------------------------------------------------------------------


def _dates(n: int = 30) -> list[pd.Timestamp]:
    """n deterministic business-day sessions (predict_date = the last)."""
    return [d.normalize() for d in pd.bdate_range("2026-01-05", periods=n)]


def _panel(
    n_dates: int = 30, n_tickers: int = 8, seed: int = 0, with_extra: bool = False,
) -> pd.DataFrame:
    """SYNTHETIC PIT panel [date, ticker, y_fwd_ret, FEATURE_COLS[, FORWARD_EXTRA_COLS]].

    Same shape as ``test_forward_commit_core._panel`` (the canonical fixture).
    """
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
        "phase": PHASE,
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


def _write_prices(
    tmp_path: Path, tickers: list[str],
    predict_ts: str = PREDICT_TS, target_t: str = TARGET_T,
) -> Path:
    """SYNTHETIC wide price parquet with rows at BOTH predict_ts and target_t.

    ``fetch_realized_forward_returns`` looks up the exact naive index timestamps
    (``pd.Timestamp(predict_ts).tz_localize(None)``), so the fixture mirrors that:
    tz-naive month-end session closes 20:00:00. Deterministic monotone prices per
    ticker (``T0 < T1 < ...``) so IC is computable for every arm (8 merged rows).
    """
    p0 = pd.Timestamp(predict_ts).tz_localize(None)
    t0 = pd.Timestamp(target_t).tz_localize(None)
    rows: dict[str, dict[pd.Timestamp, float]] = {}
    for i, t in enumerate(tickers):
        rows[t] = {p0: 100.0 + i, t0: 105.0 + 1.5 * i}  # monotone +5%..+8% returns
    prices = pd.DataFrame(rows)
    prices.index.name = "date"
    path = tmp_path / "prices.parquet"
    prices.to_parquet(path)
    return path


def _commit_and_seal(tmp_path: Path) -> tuple[Path, dict]:
    """Run the COMMIT stage; return (runs_dir, commit result dict)."""
    panel_base = _panel(n_dates=30, n_tickers=8, seed=0)
    panel_e13 = _panel(n_dates=30, n_tickers=8, seed=0, with_extra=True)
    runs_dir = tmp_path / "runs"
    res = FC.run_forward_commit(
        predict_ts=PREDICT_TS, target_t=TARGET_T,
        panel_base=panel_base, panel_e13=panel_e13, config=_base_config(),
        iset_sha256="i" * 64, provider="glm", provider_cutoff="2026-07-31",
        runs_dir=runs_dir,
    )
    return runs_dir, res


# ---------------------------------------------------------------------------
# the E2E chain: commit -> fast-forward 21 -> reveal/score -> accumulate (I1/I2/I9)
# ---------------------------------------------------------------------------


def test_e2e_commit_to_accumulate_full_chain(tmp_path: Path) -> None:
    """The full hermetic chain: COMMIT -> REVEAL (I1 gate) -> SCORE -> I2 -> ACCUMULATE -> I9.

    Stage assertions:
      COMMIT:     committed=True, 64-hex config_sha256, LONG {ticker, arm, score}
                  parquet under runs/forward/<csha>/scores_<predict_ts>.parquet,
                  8 tickers x 2 arms = 16 rows, both arms; the ledger commit row
                  is re-read from the ledger and consumed by the reveal path.
      I1 gate:    reveal with now < target_t -> both arms revealed=False with
                  reason containing 'before_target_t'; NO scored rows appended.
      SCORE:      reveal with now >= target_t -> both arms revealed=True,
                  ic_point is a float; exactly one forward_outcome_scored row
                  per arm exists in the ledger.
      I2:         a second reveal at now >= target_t appends nothing (row count
                  stable, same ic_point, _appended=False).
      ACCUMULATE: n_months==1; ic_forward is a Series on the predict_ts month
                  (PeriodIndex 2026-07); summary carries the full key set and
                  dm_flag == 'degenerate' (a single month cannot be estimated).
      I9:         the ONLY writes under the tmp runs dir are forward/ +
                  ledger.jsonl - runs/results/ NEVER exists (the confirmatory
                  ledger is untouched by the forward chain).
    """
    runs_dir, res = _commit_and_seal(tmp_path)
    prices_path = _write_prices(tmp_path, [f"T{i}" for i in range(8)])

    # -- COMMIT (Slice 3d) ---------------------------------------------------
    assert res["committed"] is True
    csha = res["config_sha256"]
    assert isinstance(csha, str) and len(csha) == 64
    scores_parquet = runs_dir / "forward" / csha / "scores_20260731T2000000000.parquet"
    assert scores_parquet.exists()
    df = pd.read_parquet(scores_parquet)
    assert set(df.columns) == {"ticker", "arm", "score"}
    assert set(df["arm"]) == {"arm_base", "arm_e13"}
    assert len(df) == 16  # 8 tickers x 2 arms

    # the reveal path consumes the ledger commit row (not the API result)
    commits = FL.read_forward_rows(runs_dir=runs_dir, config_sha256=csha, event=FL.EVENT_COMMIT)
    assert len(commits) == 1
    commit_row = commits[0]
    assert commit_row["scores_sha256"] == res["scores_sha256"]

    # -- REVEAL + SCORE (Slice 4b) - I1 gate first ---------------------------
    early = FS.reveal_and_score_forward_month(
        commit_row, prices_path=prices_path, runs_dir=runs_dir, now=NOW_BEFORE,
    )
    for arm in ("arm_base", "arm_e13"):
        assert early[arm]["revealed"] is False
        assert "before_target_t" in early[arm]["reason"]
    assert len(FL.read_forward_rows(
        runs_dir=runs_dir, config_sha256=csha, event=FL.EVENT_SCORED,
    )) == 0  # I1: no scored row may exist before the outcome realizes

    scored = FS.reveal_and_score_forward_month(
        commit_row, prices_path=prices_path, runs_dir=runs_dir, now=NOW_AFTER,
    )
    for arm in ("arm_base", "arm_e13"):
        assert scored[arm]["revealed"] is True
        assert isinstance(scored[arm]["ic_point"], float)
    scored_rows = FL.read_forward_rows(
        runs_dir=runs_dir, config_sha256=csha, event=FL.EVENT_SCORED,
    )
    assert len(scored_rows) == 2
    assert {r["arm"] for r in scored_rows} == {"arm_base", "arm_e13"}

    # -- I2 idempotency: a second reveal appends nothing ---------------------
    again = FS.reveal_and_score_forward_month(
        commit_row, prices_path=prices_path, runs_dir=runs_dir, now=NOW_AFTER,
    )
    for arm in ("arm_base", "arm_e13"):
        assert again[arm]["_appended"] is False
        assert again[arm]["ic_point"] == scored[arm]["ic_point"]
    assert len(FL.read_forward_rows(
        runs_dir=runs_dir, config_sha256=csha, event=FL.EVENT_SCORED,
    )) == 2  # no duplicate scored rows

    # -- ACCUMULATE (Slice 4c) -----------------------------------------------
    acc = FS.accumulate_forward_ic_series(config_sha256=csha, runs_dir=runs_dir)
    assert acc["n_months"] == 1
    ic_forward = acc["ic_forward"]
    assert isinstance(ic_forward, pd.Series)
    assert len(ic_forward) == 1
    assert ic_forward.index[0] == pd.Period("2026-07", freq="M")  # predict_ts month
    summary = acc["summary"]
    assert {
        "mean_diff", "se_hac", "ci_half", "ci_lo", "ci_hi",
        "dm_stat", "dm_p_mbb", "dm_flag", "n_months", "publishable_ci_half",
    }.issubset(summary.keys())
    assert summary["n_months"] == 1
    assert summary["dm_flag"] == "degenerate"  # 1 month: no variance to estimate

    # -- I9: forward chain writes ONLY forward/ + ledger.jsonl ---------------
    assert not (runs_dir / "results").exists()  # confirmatory ledger untouched
    entries = sorted(p.name for p in runs_dir.iterdir())
    assert entries == ["forward", "ledger.jsonl"]


# ---------------------------------------------------------------------------
# I2 - the sealed scores parquet is content-addressed and immutable
# ---------------------------------------------------------------------------


def test_e2e_scores_parquet_immutable_sha256(tmp_path: Path) -> None:
    """I2: the committed parquet's bytes are stable, auditable, and mutation-detectable.

    Re-reading the sealed scores parquet yields an identical sha256 (deterministic
    bytes, H6), that hash equals the commit row's ``scores_sha256`` (the ledger
    commitment is a real content hash of the artifact - anyone can re-verify it),
    and a single-byte mutation of the parquet flips the hash (tampering with a
    sealed prediction is detectable, never silently absorbed).
    """
    runs_dir, res = _commit_and_seal(tmp_path)
    csha = res["config_sha256"]
    parquet = runs_dir / "forward" / csha / "scores_20260731T2000000000.parquet"
    assert parquet.exists()

    h1 = hashlib.sha256(parquet.read_bytes()).hexdigest()
    h2 = hashlib.sha256(parquet.read_bytes()).hexdigest()
    assert h1 == h2                        # byte-stable across re-reads (H6)
    assert h1 == res["scores_sha256"]      # the commit seals THIS artifact's bytes

    commits = FL.read_forward_rows(runs_dir=runs_dir, config_sha256=csha, event=FL.EVENT_COMMIT)
    assert len(commits) == 1
    assert commits[0]["scores_sha256"] == h1  # ledger commitment matches the file

    # mutate a single byte of the sealed artifact -> the hash flips (I2 detection)
    mutated = bytearray(parquet.read_bytes())
    mutated[len(mutated) // 2] ^= 0xFF
    parquet.write_bytes(bytes(mutated))
    assert hashlib.sha256(parquet.read_bytes()).hexdigest() != h1
