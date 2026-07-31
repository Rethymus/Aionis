"""E3 Slice 3d - the forward-commit step (fit-on-I_t -> commit).

At a month-end predict timestamp ``predict_ts``, fit ONE frozen LightGBM per arm
on the PIT panel (train = ``date <= predict_date - embargo``; test = the
``predict_date`` cross-section), assemble the LONG ``[ticker, arm, score]`` panel
for both arms, and COMMIT it via :func:`forward_ledger.commit_forward_prediction`
- sha256-sealed BEFORE its t+21 outcome can realize (I1).

ORDER (the per-prediction analog of ``config_committed BEFORE result``):
  freeze I_t (Slice 3c) -> ``config_sha256(config)`` -> single fit per arm ->
  commit. All four steps complete BEFORE any reveal.

Reuses, does not reinvent:
  * :func:`aionis.eval.learner.LightGBMFrozen.fit_predict` - the ONLY fit method
    (H6 frozen params; NaNs handled natively, no imputation);
  * :func:`aionis.reporting.forward_ledger.commit_forward_prediction` /
    :func:`config_sha256` - the per-prediction sha256-seal + I2 immutability;
  * :func:`aionis.extraction.providers.build_providers` - the policy router, here
    filtered to the SINGLE pinned provider ``glm`` (I6);
  * ``eval.phase_e1.FEATURE_COLS`` - the arm_base fundamentals feature set.

I4 (no lookahead): :func:`pit_train_test_split` slices the train block to end at
least ``embargo_sessions`` before ``predict_date`` on the panel's own date grid,
and the test cross-section is exactly the predict-date rows (PIT masking is
deferred to ``mask_panel_to_pit`` upstream in ``two_arm._clean_panel``).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import structlog

from aionis.eval.learner import FROZEN_PARAMS, LightGBMFrozen
from aionis.eval.phase_e1 import FEATURE_COLS as _E1_FEATURE_COLS
from aionis.extraction.providers import Provider, build_providers
from aionis.features.frozen_beta import FROZEN_BETA_SHA256
from aionis.reporting import forward_ledger as FL

log = structlog.get_logger()

PHASE = "E3"
HORIZON = 21
EMBARGO = 21
PINNED_PROVIDER = "glm"

# arm_base = fundamentals only (mirror eval.phase_e1 arm_base, align_on="end_lag").
FEATURE_COLS: list[str] = list(_E1_FEATURE_COLS)
# arm_e13 = arm_base + Pass-A's build_forward_extra_features output columns.
FORWARD_EXTRA_COLS: list[str] = [
    "self_13d_fwd",
    "self_8k_fwd",
    "peer_13d_fwd",
    "peer_8k_fwd",
    "macro_causal_shock",
    "mech_earnings_signal",
    "mech_ownership_change",
    "mech_guidance",
    "mech_other",
]

_Y_COL = "y_fwd_ret"


# ---------------------------------------------------------------------------
# I4 - PIT train/test split (no lookahead in the train block)
# ---------------------------------------------------------------------------


def pit_train_test_split(
    panel: pd.DataFrame,
    predict_date,
    embargo_sessions: int = EMBARGO,
    *,
    membership: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split the panel into a no-lookahead train block and the predict-date test cross-section.

    ``train = panel[date <= predict_date - embargo_sessions]`` measured on the
    panel's OWN sorted date grid (so the embargo is a whole-sessions gap, not a
    calendar guess); ``test = panel[date == predict_date]``.

    I4 guarantee: the train block's max date index is ``<= predict_date index -
    embargo`` (no leaked future rows). The test cross-section is exactly the
    predict-date rows - NO forward-fill is applied here (PIT constituent masking
    is deferred to :func:`mask_panel_to_pit` upstream). When ``membership`` is
    provided, a belt-and-suspenders check asserts the test tickers equal
    :func:`constituents_on(predict_date)` so a forward-fill mismatch surfaces as
    a hard error rather than silent fabrication.
    """
    pdate = pd.Timestamp(predict_date).normalize()
    dates_sorted = pd.DatetimeIndex(sorted(panel["date"].unique()))
    pos = {d: i for i, d in enumerate(dates_sorted)}

    test = panel[panel["date"] == pdate].reset_index(drop=True)

    if pdate in pos:
        cutoff_idx = pos[pdate] - embargo_sessions
    else:
        cutoff_idx = -1  # predict_date absent -> empty train (no fabrication)
    if cutoff_idx < 0:
        # cutoff before the first grid date -> train is empty
        train = panel.iloc[0:0].reset_index(drop=True)
    else:
        cutoff = dates_sorted[cutoff_idx]
        train = panel[panel["date"] <= cutoff].reset_index(drop=True)

    # I4: assert no lookahead in the train block (grid-indexed embargo gap)
    if len(train) and pdate in pos:
        train_max_pos = pos[train["date"].max()]
        assert train_max_pos <= pos[pdate] - embargo_sessions, (
            f"I4 lookahead: train max date index {train_max_pos} > "
            f"predict index {pos[pdate]} - embargo {embargo_sessions}"
        )

    # I4: no universe forward-fill - if membership is given, the test cross-section
    # must equal the PIT constituents exactly (a mismatch means upstream PIT masking
    # was skipped; surface it, never fabricate).
    if membership is not None and len(test):
        from aionis.ingest.universe import constituents_on

        pit = constituents_on(membership, pdate)
        assert set(test["ticker"]) == pit, (
            f"I4 universe mismatch: test tickers {sorted(set(test['ticker']))} != "
            f"PIT constituents {sorted(pit)} at {pdate.isoformat()} (no forward-fill)"
        )
    return train, test


# ---------------------------------------------------------------------------
# frozen config (sha256-sealed BEFORE any score; flips on any lever -> I6/I8)
# ---------------------------------------------------------------------------


def build_forward_config(
    *,
    horizon: int,
    shas: dict,
    versions: dict,
    provider: str,
    provider_cutoff: str,
    causal_schema_version: str,
    mechanism_keyword_enum: list[str],
    ff12_taxonomy: list[str],
    broadcast_weights: dict,
    frozen_params: dict,
    frozen_beta_sha256: str = FROZEN_BETA_SHA256,
) -> dict:
    """Build the frozen E3 forward config (mirrors ``phase_e1.build_config`` shape).

    Every lever that could move the OOS score is committed here so
    :func:`config_sha256` over this dict is the durable forward-sequence key (I8):
    changing the provider (I6), the causal schema, the mechanism enum, the FF-12
    taxonomy, the frozen-β broadcast weights, the frozen learner params, OR any
    input sha yields a new hash -> a new forward sequence.

    I8 (silent-mutation guards):
      * ``frozen_beta_sha256`` - a CONTENT hash of the frozen-β sign table (not
        just the version string), so a sign flip WITHIN a version is a new
        sequence (no rerun-to-significance via the macro channel).
      * ``frozen_params`` - the FULL ``learner.FROZEN_PARAMS`` dict (the canonical
        hyperparameters the frozen learner actually uses), not a caller-supplied
        2-key subset; any hyperparameter flip (n_estimators / learning_rate / …)
        flips the sig. Caller overrides merge on top of the canonical base.
    """
    cfg: dict = {
        "phase": PHASE,
        "mode": "exploratory",
        "align_on": "end_lag",
        "horizon": horizon,
        "embargo_sessions": EMBARGO,
        "feature_cols_base": list(FEATURE_COLS),
        "feature_cols_e13": list(FEATURE_COLS) + list(FORWARD_EXTRA_COLS),
        "causal_schema_version": causal_schema_version,
        "mechanism_keyword_enum": sorted(mechanism_keyword_enum),
        "ff12_taxonomy": sorted(ff12_taxonomy),
        "broadcast_weights": broadcast_weights,
        "frozen_beta_sha256": frozen_beta_sha256,
        "frozen_params": {**FROZEN_PARAMS, **frozen_params},
        "provider": provider,
        "provider_cutoff": provider_cutoff,
        "versions": versions,
    }
    cfg.update(shas)
    return cfg


# ---------------------------------------------------------------------------
# single fit per arm (no CV - one fit_predict call)
# ---------------------------------------------------------------------------


def fit_forward_single(
    panel: pd.DataFrame, predict_date, feature_cols: list[str], *, embargo: int = EMBARGO,
    membership: pd.DataFrame | None = None,
) -> pd.Series:
    """Fit ONE frozen LightGBM on the PIT train block, predict the predict-date cross-section.

    A single :func:`LightGBMFrozen.fit_predict` call (no CV, no early stopping) -
    the forward analog of ``phase_e1.run_confirmatory``'s single-fit-at-t. Returns
    a Series of scores indexed like the test rows.

    ``membership`` (optional) opt-ins the no-forward-fill PIT-membership assert in
    :func:`pit_train_test_split` (defense in depth: the live runner passes the real
    membership; hermetic tests may omit it).
    """
    train, test = pit_train_test_split(
        panel, predict_date, embargo_sessions=embargo, membership=membership,
    )
    if len(train) == 0:
        raise ValueError(
            "fit_forward_single: empty train block (panel shorter than embargo + 1 sessions)"
        )
    if len(test) == 0:
        raise ValueError(
            "fit_forward_single: empty test block (predict_date not in the panel)"
        )
    return LightGBMFrozen().fit_predict(train, test, feature_cols, _Y_COL)


# ---------------------------------------------------------------------------
# I6 - resolve the SINGLE pinned provider (glm)
# ---------------------------------------------------------------------------


def resolve_pinned_provider(name: str = PINNED_PROVIDER) -> Provider:
    """Return the SINGLE enabled pinned provider (default ``glm``); raise if missing.

    I6: the forward sequence pins ONE provider (GLM-4-Flash, priority-1, free) so
    a provider swap is a deliberate new sequence (pre-reg §5), never a silent
    fallback. Raises if the pinned provider is not enabled (no key / disabled).
    """
    providers = build_providers(only_enabled=True)
    for p in providers:
        if p.name == name:
            return p
    raise RuntimeError(
        f"I6: pinned provider '{name}' is not enabled (have: {[p.name for p in providers]}). "
        f"Set the {name.upper()}_API_KEY / OPENAI_API_KEY in .env or pin a different provider "
        "(a provider swap is a new forward sequence per pre-reg §5)."
    )


# ---------------------------------------------------------------------------
# the forward-commit step (freeze -> config -> fit -> commit)
# ---------------------------------------------------------------------------


def _scores_sig(long: pd.DataFrame) -> str:
    """Deterministic sha256 of the LONG scores panel (what a commit WOULD seal).

    Mirrors :func:`forward_ledger.commit_forward_prediction`'s internal
    scores_sha256 so ``no_ledger=True`` reports the SAME sig a real commit would
    record (the dry-run is faithful to the live path).
    """
    norm = FL._normalize_scores(long)
    return hashlib.sha256(FL._deterministic_parquet_bytes(norm)).hexdigest()


def run_forward_commit(
    *,
    predict_ts: str,
    target_t: str,
    panel_base: pd.DataFrame,
    panel_e13: pd.DataFrame,
    config: dict,
    iset_sha256: str,
    provider: str,
    provider_cutoff: str,
    runs_dir: Path | str,
    mode: str = "exploratory",
    no_ledger: bool = False,
    membership: pd.DataFrame | None = None,
) -> dict:
    """Run the forward-commit step: config seal -> single fit per arm -> commit.

    ORDER (I1): :func:`config_sha256` is computed BEFORE any fit; the fit precedes
    the commit; the commit is sha256-sealed BEFORE its ``target_t`` outcome can
    realize. Refuses a non-``glm`` provider (I6).

    Assembles the LONG ``[ticker, arm, score]`` panel (arm in {arm_base,
    arm_e13}) and commits it via :func:`commit_forward_prediction` unless
    ``no_ledger=True`` (in which case the sig is still computed for the dry-run but
    nothing is written). Returns the commit/sig result dict.

    ``membership`` (optional) activates the PIT no-forward-fill assert on the test
    cross-section in the live fit path (defense in depth). Existing callers that
    omit it keep the prior behavior (assert is opt-in).
    """
    if provider != PINNED_PROVIDER:
        raise ValueError(
            f"I6: forward commit refused for provider='{provider}'; only "
            f"'{PINNED_PROVIDER}' is the pinned forward provider (a provider swap "
            "is a new forward sequence per pre-reg §5)."
        )

    # 1. seal the config sha256 BEFORE any score exists (I1 ordering anchor)
    csha = FL.config_sha256(config)

    # 2. single fit per arm (predict_date = the panel's last session)
    predict_date = panel_base["date"].max()
    scores_base = fit_forward_single(
        panel_base, predict_date, config["feature_cols_base"], membership=membership,
    )
    scores_e13 = fit_forward_single(
        panel_e13, predict_date, config["feature_cols_e13"], membership=membership,
    )

    test_base = panel_base[panel_base["date"] == predict_date]
    test_e13 = panel_e13[panel_e13["date"] == predict_date]
    long = pd.concat(
        [
            pd.DataFrame(
                {"ticker": test_base["ticker"].to_numpy(), "arm": "arm_base",
                 "score": scores_base.to_numpy(dtype=float)}
            ),
            pd.DataFrame(
                {"ticker": test_e13["ticker"].to_numpy(), "arm": "arm_e13",
                 "score": scores_e13.to_numpy(dtype=float)}
            ),
        ],
        ignore_index=True,
    )

    result: dict = {
        "predict_ts": predict_ts,
        "target_t": target_t,
        "config_sha256": csha,
        "committed": False,
        "scores_sha256": _scores_sig(long),
    }

    if no_ledger:
        log.info(
            "forward_commit_dry_run", predict_ts=predict_ts, config_sha256=csha,
            scores_sha256=result["scores_sha256"],
        )
        return result

    # 3. commit (sha256-seal the scores parquet + append the ledger row)
    commit = FL.commit_forward_prediction(
        predict_ts, target_t, long, config, iset_sha256, provider, provider_cutoff,
        runs_dir=runs_dir, mode=mode,
    )
    result["committed"] = bool(commit.get("committed", False))
    result["scores_sha256"] = commit.get("scores_sha256", result["scores_sha256"])
    result["_appended"] = commit.get("_appended")
    return result


__all__ = [
    "PHASE",
    "HORIZON",
    "EMBARGO",
    "PINNED_PROVIDER",
    "FEATURE_COLS",
    "FORWARD_EXTRA_COLS",
    "pit_train_test_split",
    "build_forward_config",
    "fit_forward_single",
    "resolve_pinned_provider",
    "run_forward_commit",
]
