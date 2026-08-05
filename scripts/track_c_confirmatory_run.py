#!/usr/bin/env python3
"""Track C confirmatory OOS run — first confirmatory climax (owner D6 GO 2026-08-05).

Loads frozen config #48 (sig ``e14b9d44...``), runs the 41-feature joint US-CN
chronological walk-forward estimator TWICE with an independent H6 bit-identical
assertion, applies the Jennison-Turnbull group-sequential equivalence gate
(ADR-010 Amendment 2026-08-01) at the reachable look(s) on the combined
rank-IC series, and writes the ``confirmatory:first`` ledger row.

ESTIMAND (documented choice): the gated quantity is the **combined rank-IC
series mean** (equal-weight per-region monthly IC of the 41-feature treatment
model). The conditional-IC beta (regime interaction) is reported as explanatory
and is NOT a separate gated hypothesis — multiplicity budget stays at 1.
Rationale: frozen #48 ``jt_gate.rule`` is "RCI_k strict-containment within
[-0.010,+0.010]" operating on rank-IC; ``cond_beta`` is a single regression
coefficient with no natural monthly series for the group-sequential gate.

ANTI-LEAKAGE ANCHORS:
  * **config_committed BEFORE result.** Config #48 was frozen before this run
    observed any 41-feature confirmatory OOS metric. This script verifies
    ``track_c_amend2.build_amendment()`` reproduces sig ``e14b9d44...`` — if
    anyone mutates the amendment code, the sig check fails hard.
  * **H6 determinism.** The estimator runs TWICE; ``combined_ic_series``,
    ``us_ic_series``, ``cn_ic_series`` and ``oos_scores`` must be bit-identical
    across runs (n_jobs=1, seed=0, version-pinned via uv.lock).
  * **Fixed gate.** The J-T gate is a deterministic function of the IC series
    + the frozen looks/SESOI/alpha — no post-hoc tuning, no rerun-to-significance.
  * **Prior-exploratory disclosure.** The asym41 exploratory run (2026-08-05
    13:48) observed combined IC ~ -0.0088 BEFORE this confirmatory sediment.
    Config #48 was chosen by D1-D5 spec decisions (machinery readiness + spec
    faithfulness), NOT by IC optimization; H6 determinism guarantees this
    confirmatory run reproduces the same IC.

GATING:
  * ``TRACK_C_CONFIRMATORY_GO=1`` (owner GO) appends the ``confirmatory:first``
    row to ``runs/ledger.jsonl``.
  * Default = DRY-RUN (computes + prints everything, writes NO ledger).

Run::

    uv run python scripts/track_c_confirmatory_run.py                       # dry-run
    TRACK_C_CONFIRMATORY_GO=1 uv run python scripts/track_c_confirmatory_run.py
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from aionis.config import settings
from aionis.eval.rank_ic import rank_ic_summary
from aionis.eval.sesoi_gate import look_summary
from aionis.eval.track_c_joint import TrackCJointResult, build_joint_panel, fit_track_c_joint
from aionis.features.macro_headline import MACRO_HEADLINE_6, join_macro_to_joint_panel
from aionis.features.price_features import TRACK_B_PRICE_FEATURE_COLS

# Reuse the tested config_sig mechanism + ledger path (track_c_commit).
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from track_c_amend2 import build_amendment  # noqa: E402
from track_c_commit import LEDGER, PHASE, config_sig  # noqa: E402

# ---------------------------------------------------------------------------
# Frozen references (ledger #48, ADR-010 Amendment 2026-08-01)
# ---------------------------------------------------------------------------

FROZEN_SIG_48 = "e14b9d445411e74cc3418af3bde1148163725875b01ab75175bdde002225e738"
LOOKS: tuple[int, ...] = (60, 90, 120)  # ADR-010 group-sequential look months
SESOI = 0.010  # frozen sesoi_rank_ic (#46/#48)
ALPHA = 0.05  # ADR-010 family-wise alpha

US_PANEL = settings.data_dir / "cache" / "track_b_panel.parquet"
CN_PANEL = settings.data_dir / "cache" / "cn_price_panel.parquet"
REGIME_PANEL = settings.data_dir / "cache" / "regime_composite.parquet"
WINDOW_START = "2016-01-01"  # ledger #46 universe.{us,cn}.window_start

# 41-feature confirmatory feature_cols (must match #48 d4_feature_cols).
US_FUNDAMENTALS_13 = [
    "roa", "roe", "profit_margin", "asset_growth_1m", "asset_growth_12m",
    "revenue_growth_1m", "revenue_growth_12m", "equity_growth_1m",
    "leverage", "debt_to_equity", "book_value_per_share", "accruals",
    "investment_12m",
]
CN_EXTRAS_2 = ["limit_up_down_distance", "suspension_flag"]
US_23 = US_FUNDAMENTALS_13 + list(TRACK_B_PRICE_FEATURE_COLS)
CN_12 = list(TRACK_B_PRICE_FEATURE_COLS) + CN_EXTRAS_2
UNION_35 = sorted(set(US_23) | set(CN_12))  # 25 unique column names
FEATURE_COLS_41 = UNION_35 + MACRO_HEADLINE_6  # 31 unique names; 41 per-region assignments


# ---------------------------------------------------------------------------
# Pure helpers (hermetic-testable)
# ---------------------------------------------------------------------------

def verify_frozen_config() -> dict:
    """Rebuild #48 config in-process and assert its sha256 matches the frozen row.

    Raises SystemExit if ``track_c_amend2.build_amendment()`` does not reproduce
    the frozen sig — guards against silent amendment code drift.
    """
    cfg = build_amendment()
    sig = config_sig(cfg)
    if sig != FROZEN_SIG_48:
        raise SystemExit(
            f"[FROZEN MISMATCH] config_sig={sig} != frozen #48 {FROZEN_SIG_48}. "
            "track_c_amend2.build_amendment() must reproduce the frozen row exactly; "
            "aborting before any OOS observation."
        )
    return cfg


def assert_h6_identical(r1: TrackCJointResult, r2: TrackCJointResult) -> None:
    """Assert two estimator runs produce bit-identical IC series + oos_scores.

    Uses pandas NaN-aware ``.equals`` plus a byte-level ``.tobytes`` check on
    each IC series (belt-and-suspenders for H6 determinism).
    """
    for field in ("combined_ic_series", "us_ic_series", "cn_ic_series"):
        s1 = getattr(r1, field).sort_index()
        s2 = getattr(r2, field).sort_index()
        if not s1.equals(s2):
            raise AssertionError(f"H6 FAIL: {field} differs (pandas .equals)")
        if s1.to_numpy().tobytes() != s2.to_numpy().tobytes():
            raise AssertionError(f"H6 FAIL: {field} differs (byte-level)")
    if not r1.oos_scores.equals(r2.oos_scores):
        raise AssertionError("H6 FAIL: oos_scores differs")
    # CSV-roundtrip hash as a stable, human-inspectable fingerprint.
    h1 = _csv_sha256(r1.oos_scores)
    h2 = _csv_sha256(r2.oos_scores)
    if h1 != h2:
        raise AssertionError(f"H6 FAIL: oos_scores csv hash {h1[:8]} != {h2[:8]}")


def _csv_sha256(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return hashlib.sha256(buf.getvalue().encode()).hexdigest()


def jt_reachable_looks(
    ic_series: pd.Series,
    looks: tuple[int, ...] = LOOKS,
    sesoi: float = SESOI,
    alpha: float = ALPHA,
) -> list[dict]:
    """Evaluate the J-T gate at every reachable look (n_obs <= len(series)).

    Returns a list (one entry per planned look). Reachable looks carry the full
    ``look_summary`` dict; pending looks carry a ``status`` note.
    """
    out: list[dict] = []
    n = len(ic_series)
    for k, n_obs in enumerate(looks, start=1):
        if n >= n_obs:
            out.append(look_summary(ic_series, k=k, looks=looks, sesoi=sesoi, alpha=alpha))
        else:
            out.append({
                "look": k,
                "n_obs_planned": n_obs,
                "status": f"PENDING (have {n} months, need {n_obs})",
            })
    return out


def build_confirmatory_row(
    *,
    result: TrackCJointResult,
    jt_looks: list[dict],
    full_summary: dict,
    n_months_banked: int,
) -> dict:
    """Construct the ``confirmatory:first`` ledger row (pure; no I/O)."""
    look1 = jt_looks[0]
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "confirmatory:first",
        "phase": PHASE,
        "config_sig": FROZEN_SIG_48,
        "config_sig_source": "track_c_amend2.build_amendment() (#46+#47+#48 cumulative)",
        "estimand": (
            "combined rank-IC series mean (equal-weight per-region monthly IC) of the "
            "41-feature joint US-CN treatment model; cond_beta reported explanatory only"
        ),
        "n_months_ic": int(len(result.combined_ic_series)),
        "n_walk_folds": int(result.n_walk_folds),
        "combined_ic": {
            "mean": float(full_summary["mean_ic"]),
            "se_hac": float(full_summary["se_hac"]),
            "t_hac": float(full_summary["t_hac"]),
            "p_hac": float(full_summary["p_hac"]),
            "ci_95_half": float(full_summary["ci_half"]),
            "maxlag": int(full_summary["maxlag"]),
            "n": int(full_summary["n"]),
        },
        "per_region_ic": {
            "us_mean": float(result.us_ic_series.mean()),
            "cn_mean": float(result.cn_ic_series.mean()),
            "us_n": int(len(result.us_ic_series)),
            "cn_n": int(len(result.cn_ic_series)),
        },
        "conditional_ic_explanatory": {
            "role": (
                "single pre-specified interaction (score x regime_state); NOT a separate "
                "gated hypothesis (multiplicity budget 1)"
            ),
            "alpha": float(result.cond_alpha),
            "alpha_p": float(result.cond_alpha_p),
            "beta": float(result.cond_beta),
            "beta_p": float(result.cond_beta_p),
            "r_squared": float(result.cond_r_squared),
            "n_months": int(result.cond_n_months),
        },
        "jt_gate": {
            "rule": (
                "ADR-010 Amendment 2026-08-01: Jennison-Turnbull OBF group-sequential "
                "equivalence; RCI_k strict-containment within [-0.010,+0.010]"
            ),
            "looks_planned_months": list(LOOKS),
            "sesoi": SESOI,
            "alpha": ALPHA,
            "looks": jt_looks,
            "look1_verdict": (
                look1.get("verdict", "PENDING") if isinstance(look1, dict) else "PENDING"
            ),
            "banked_months_toward_look2": int(n_months_banked),
            "note": (
                f"look-1 evaluated at n=60 (planned); {n_months_banked} months banked toward "
                f"look-2 (needs 90); look-3 needs 120 (reachable only via E3 forward-live)"
            ),
        },
        "H6_deterministic": True,
        "feature_cols_per_region": 41,
        "feature_cols_union_unique": len(FEATURE_COLS_41),
        "notes": {
            "prior_exploratory": (
                "asym41 EXPLORATORY run (2026-08-05 13:48) observed combined IC ~ -0.0088 "
                "BEFORE this confirmatory sediment. Config #48 was chosen by D1-D5 spec "
                "decisions (machinery readiness + spec faithfulness), NOT by IC optimization. "
                "H6 determinism guarantees this confirmatory run reproduces the same IC."
            ),
            "cn_gdp": (
                "NaN (annual releases < Z_MIN=12; LightGBM native missing; data limit disclosed)"
            ),
            "regime_source": (
                "regime_composite.parquet (existing 2/3-layer composite; CN meso US-only "
                "per Lane A 2026-08-04 shenwan-meso-7gate verdict)"
            ),
            "estimand_choice": (
                "J-T gate applies to combined rank-IC series mean (Reading A); cond_beta is "
                "the explicit regime-interaction test, reported but not gated. The model "
                "implicitly conditions on regime via macro_headline_6 features."
            ),
            "independence_caveat": (
                "J-T gate + H6 + sediment computed by opus orchestrator directly (subagent "
                "dispatch [1210]-flaky today). Independence via deterministic reproducibility: "
                "any party can rerun from frozen #48 + this script and verify bit-identical."
            ),
        },
    }


# ---------------------------------------------------------------------------
# Estimator execution
# ---------------------------------------------------------------------------

def _build_panel() -> pd.DataFrame:
    """Build the 41-feature joint panel ONCE (macro join parses 30MB DFF cache;
    repeated work would double runtime for no H6 value)."""
    for p in (US_PANEL, CN_PANEL, REGIME_PANEL):
        if not p.exists():
            raise SystemExit(f"[ERROR] missing {p}")

    joint = build_joint_panel(
        US_PANEL,
        CN_PANEL,
        feature_cols=[],
        us_feature_cols=US_23,
        cn_feature_cols=CN_12,
        window_start=WINDOW_START,
    )
    return join_macro_to_joint_panel(joint)


def _load_regime() -> pd.Series:
    regime_df = pd.read_parquet(REGIME_PANEL)
    if "regime_state" not in regime_df.columns:
        raise SystemExit(f"[ERROR] {REGIME_PANEL} has no 'regime_state' column")
    regime_df.index = pd.to_datetime(regime_df.index)
    return regime_df["regime_state"].sort_index()


def _fit(panel: pd.DataFrame, regime_state: pd.Series) -> TrackCJointResult:
    """Run the frozen 41-feature joint estimator (H6: deterministic given panel)."""
    return fit_track_c_joint(
        panel=panel,
        feature_cols=FEATURE_COLS_41,
        regime_state=regime_state,
        horizon=21,
        min_train_months=60,
        embargo_sessions=21,
        bin_count=5,
    )


def _save_artifacts(result: TrackCJointResult, row: dict) -> None:
    """Persist gitignored confirmatory artifacts (oos_scores, ic_series, summary)."""
    out_dir = settings.data_dir.parent / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    result.oos_scores.to_parquet(out_dir / "track_c_confirmatory_oos_scores.parquet")
    pd.concat(
        [
            result.us_ic_series.rename("us"),
            result.cn_ic_series.rename("cn"),
            result.combined_ic_series.rename("combined"),
        ],
        axis=1,
        sort=True,
    ).to_parquet(out_dir / "track_c_confirmatory_ic_series.parquet")
    (out_dir / "track_c_confirmatory_summary.json").write_text(
        json.dumps(row, indent=2, default=str), encoding="utf-8"
    )


def _ledger_row_count() -> int:
    if not LEDGER.exists():
        return 0
    with LEDGER.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def _commit_from_artifact(out_dir: Path) -> int:
    """Owner-authorized persist path: load the dry-run's verified summary.json
    and append its ``confirmatory:first`` row to the ledger.

    The dry-run already proved H6 (double-run bit-identical) and computed the
    J-T gate on the real frozen-#48 panel. This path simply persists that
    verified row — it does NOT re-observe or re-compute. Anti-leakage holds:
    config #48 was frozen before the dry-run's observation; this commit only
    appends what was already observed.
    """
    summary_path = out_dir / "track_c_confirmatory_summary.json"
    if not summary_path.exists():
        raise SystemExit(
            f"[ERROR] {summary_path} not found. Run the dry-run first "
            "(it saves the verified row to summary.json)."
        )
    row = json.loads(summary_path.read_text(encoding="utf-8"))
    # Sanity: the loaded row must reference the frozen #48 sig.
    if row.get("config_sig") != FROZEN_SIG_48:
        raise SystemExit(
            "[FROZEN MISMATCH] summary.json config_sig != frozen #48; "
            "the artifact is stale or from a different config. Re-run the dry-run."
        )
    if not row.get("H6_deterministic"):
        raise SystemExit("[ERROR] summary.json H6_deterministic is not True; will not commit.")

    # Refresh the commit timestamp (the compute ts stays inside the nested fields).
    row["ts"] = datetime.now(timezone.utc).isoformat()
    row["commit_mode"] = (
        "artifact-reuse: persisted the dry-run's H6-verified confirmatory row; "
        "no recompute (anti-leakage: config #48 frozen before dry-run observation)"
    )

    pre_count = _ledger_row_count()
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    post_count = _ledger_row_count()
    print(
        f"[track_c-confirmatory] COMMITTED (from artifact) -> {LEDGER} "
        f"(confirmatory:first, row #{post_count}; was #{pre_count})",
        flush=True,
    )
    print(
        f"[track_c-confirmatory] combined IC mean={row['combined_ic']['mean']:.6f} "
        f"p_hac={row['combined_ic']['p_hac']:.4f} | look-1 verdict="
        f"{row['jt_gate']['look1_verdict']}",
        flush=True,
    )
    return 0


def main() -> int:
    owner_go = os.environ.get("TRACK_C_CONFIRMATORY_GO") == "1"
    from_artifact = os.environ.get("TRACK_C_CONFIRMATORY_FROM_ARTIFACT") == "1"
    out_dir = settings.data_dir.parent / "runs"

    if from_artifact:
        if not owner_go:
            raise SystemExit(
                "[ERROR] TRACK_C_CONFIRMATORY_FROM_ARTIFACT=1 requires "
                "TRACK_C_CONFIRMATORY_GO=1 too (owner must authorize the commit)."
            )
        print("[track_c-confirmatory] mode=GO (from artifact; no recompute)", flush=True)
        return _commit_from_artifact(out_dir)

    print(
        f"[track_c-confirmatory] mode="
        f"{'GO (will append confirmatory:first)' if owner_go else 'DRY-RUN (no ledger)'}",
        flush=True,
    )

    verify_frozen_config()
    print(f"[track_c-confirmatory] frozen #48 sig verified: {FROZEN_SIG_48[:16]}...", flush=True)
    print(
        f"[track_c-confirmatory] feature_cols union unique = {len(FEATURE_COLS_41)} "
        f"(per-region assignments = 41)",
        flush=True,
    )

    print("[track_c-confirmatory] building 41-feature joint panel (macro ONCE) ...", flush=True)
    panel = _build_panel()
    regime_state = _load_regime()
    print(f"[track_c-confirmatory] panel: {panel.shape}", flush=True)

    print("[track_c-confirmatory] estimator run #1 ...", flush=True)
    r1 = _fit(panel, regime_state)
    print("[track_c-confirmatory] estimator run #2 (H6 bit-identical assert) ...", flush=True)
    r2 = _fit(panel, regime_state)
    assert_h6_identical(r1, r2)
    print("[track_c-confirmatory] H6 bit-identical PASS", flush=True)

    ic_series = r1.combined_ic_series.sort_index()
    n_ic = int(len(ic_series))

    jt_looks = jt_reachable_looks(ic_series)
    full_summary = rank_ic_summary(ic_series)
    n_banked = max(0, n_ic - LOOKS[0])  # months beyond look-1, banked toward look-2

    row = build_confirmatory_row(
        result=r1,
        jt_looks=jt_looks,
        full_summary=full_summary,
        n_months_banked=n_banked,
    )

    look1 = jt_looks[0]
    print(
        f"[track_c-confirmatory] combined IC: mean={full_summary['mean_ic']:.6f} "
        f"p_hac={full_summary['p_hac']:.4f} n={n_ic}",
        flush=True,
    )
    if isinstance(look1, dict) and "verdict" in look1:
        print(
            f"[track_c-confirmatory] J-T look-1 verdict: {look1['verdict']} "
            f"(RCI [{look1['rci_lower']:.4f}, {look1['rci_upper']:.4f}] @ "
            f"{look1['rci_level_pct']:.2f}%)",
            flush=True,
        )
    print(
        f"[track_c-confirmatory] looks reachable: "
        f"{[lk.get('look') for lk in jt_looks if 'verdict' in lk]} / pending: "
        f"{[lk.get('look') for lk in jt_looks if 'status' in lk]}",
        flush=True,
    )

    _save_artifacts(r1, row)
    print(
        "[track_c-confirmatory] saved -> "
        "runs/track_c_confirmatory_{oos_scores,ic_series,summary}",
        flush=True,
    )

    if not owner_go:
        print(
            "[track_c-confirmatory] DRY-RUN complete. "
            "Re-run with TRACK_C_CONFIRMATORY_GO=1 to append confirmatory:first.",
            flush=True,
        )
        return 0

    pre_count = _ledger_row_count()
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    post_count = _ledger_row_count()
    print(
        f"[track_c-confirmatory] COMMITTED -> {LEDGER} "
        f"(confirmatory:first, row #{post_count}; was #{pre_count})",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
