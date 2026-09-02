"""Phase B two-arm runner — hermetic structural invariants (synthetic data).

Pins the core fairness property: with NO fundamentals, both arms build IDENTICAL
panels (align_on has no effect) → identical folds + deterministic LightGBM →
identical scores. So any score difference on real fundamentals comes ONLY from
fundamental timing, never from arm-specific bias.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.eval.two_arm import compute_shared_folds, run_arm_oos, run_two_arm_oos


def _fixtures(seed: int = 0, n_sess: int = 120,
              tickers: tuple[str, ...] = ("A", "B", "C", "D")) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-02", periods=n_sess)
    px = pd.DataFrame(
        100 + np.cumsum(rng.normal(size=(n_sess, len(tickers))), axis=0),
        index=dates, columns=list(tickers),
    )
    months = pd.date_range(dates[0], dates[-1], freq="MS")
    mem = pd.DataFrame(
        [(m, t) for m in months for t in tickers], columns=["date", "ticker"],
    )
    return px, mem


_KW = dict(
    fundamentals_long=pd.DataFrame(), horizon=5, feature_cols=["close"],
    n_splits=3, embargo_sessions=5, params={"n_estimators": 40},
)


def test_empty_fundamentals_arms_produce_identical_scores() -> None:
    px, mem = _fixtures()
    out = run_two_arm_oos(prices=px, membership=mem, **_KW)
    a, b = out["arm_state"], out["arm_base"]
    assert set(a.columns) == {"date", "ticker", "y_fwd_ret", "score"}
    assert a[["date", "ticker"]].reset_index(drop=True).equals(
        b[["date", "ticker"]].reset_index(drop=True)
    )
    # No fundamentals -> identical panels -> identical scores (no arm bias).
    np.testing.assert_array_equal(a["score"].to_numpy(), b["score"].to_numpy())


def test_deterministic_across_runs() -> None:
    px, mem = _fixtures()
    o1 = run_two_arm_oos(prices=px, membership=mem, **_KW)["arm_state"]["score"].to_numpy()
    o2 = run_two_arm_oos(prices=px, membership=mem, **_KW)["arm_state"]["score"].to_numpy()
    np.testing.assert_array_equal(o1, o2)


def test_finite_scores_and_oos_rows_present() -> None:
    px, mem = _fixtures()
    out = run_two_arm_oos(prices=px, membership=mem, **_KW)
    for arm, df in out.items():
        assert len(df) > 0, f"{arm} produced no OOS rows"
        assert np.isfinite(df["score"].to_numpy()).all()
        assert np.isfinite(df["y_fwd_ret"].to_numpy()).all()


def test_scores_differ_when_fundamental_timing_differs() -> None:
    """Guard (critic 'Missing'): when a fact's filed date != end+lag, arm_state and
    arm_base see the value at DIFFERENT times -> their OOS score arrays must differ.
    Catches a future bug that silently makes the arms identical."""
    px, mem = _fixtures()
    tickers = list(px.columns)
    # 10-K: end 2024-01-02, filed 2024-03-15 (fast filer). end+6mo = 2024-07-02,
    # which is BEYOND the ~120-session panel -> arm_base never sees fund_assets
    # (all NaN) while arm_state sees it from 2024-03-15 -> feature matrices differ.
    fund = pd.DataFrame([
        {"ticker": t, "metric": "assets", "end": "2024-01-02", "filed": "2024-03-15",
         "form": "10-K", "fy": 2023, "fp": "FY", "value": float(i + 1) * 1000.0, "unit": "USD"}
        for i, t in enumerate(tickers)
    ])
    out = run_two_arm_oos(
        prices=px, membership=mem, fundamentals_long=fund, horizon=5,
        feature_cols=["close", "fund_assets"], n_splits=3, embargo_sessions=5,
        params={"n_estimators": 40},
    )
    a = out["arm_state"].set_index(["date", "ticker"])["score"]
    b = out["arm_base"].set_index(["date", "ticker"])["score"]
    common = a.index.intersection(b.index)
    assert len(common) > 0
    assert not np.array_equal(a.loc[common].to_numpy(), b.loc[common].to_numpy()), (
        "arm_state and arm_base produced identical scores despite different fund timing"
    )


# --- Phase C feature-set axis (arm_macro = arm_base + bundle) -----------------


def test_phase_c_bundle_adds_columns_without_changing_row_layout() -> None:
    """The Phase C bundle (date-broadcast macro + per-(ticker,date) earnings) must
    add COLUMNS only — the (date, ticker) layout stays identical to arm_base, so the
    shared-fold layout assertion inside ``run_arm_oos`` still holds and both arms are
    scored on exactly the same rows (the differential then isolates the bundle)."""
    px, mem = _fixtures(seed=1, n_sess=80)
    horizon, ns, emb, params = 5, 3, 5, {"n_estimators": 40}
    folds, ref = compute_shared_folds(px, mem, horizon, n_splits=ns, embargo_sessions=emb)

    base = run_arm_oos(px, pd.DataFrame(), mem, horizon, ["close"], "filed",
                      folds, ref, params)

    # date-broadcast macro (one value per session) + per-(ticker,date) earnings
    sessions = pd.DatetimeIndex(sorted(px.index))
    macro = pd.DataFrame(
        {"macro_x": np.arange(len(sessions), dtype=float)}, index=sessions,
    )
    ref_dates = sorted(ref["date"].unique())
    ref_tickers = sorted(ref["ticker"].unique())
    earn_rows = [
        (d, t, float((d.dayofweek + ord(t)) % 7))
        for d in ref_dates for t in ref_tickers
    ]
    earn = pd.DataFrame(earn_rows, columns=["date", "ticker", "earn"])

    # If the bundle changed the (date, ticker) layout, run_arm_oos would raise
    # AssertionError here. It does not -> layout is invariant.
    macro_arm = run_arm_oos(
        px, pd.DataFrame(), mem, horizon, ["close", "macro_x", "earn"], "filed",
        folds, ref, params, macro=macro, extra_features=earn,
    )

    base_layout = base[["date", "ticker"]].reset_index(drop=True)
    macro_layout = macro_arm[["date", "ticker"]].reset_index(drop=True)
    assert macro_layout.equals(base_layout)
    # run_arm_oos returns only the score panel (columns not leaked out)
    assert set(macro_arm.columns) == {"date", "ticker", "score", "y_fwd_ret"}
    assert macro_arm["score"].notna().any()


def test_phase_c_bundle_columns_actually_consumed_by_learner() -> None:
    """Two-sided proof that the threaded extra_features column reaches the learner:

    (a) when the column is in ``feature_cols`` it changes the scores vs arm_base;
    (b) when it is NOT in ``feature_cols`` it is ignored and scores are bit-identical
    to arm_base (deterministic LightGBM, same consumed columns). Robust to the
    synthetic data having no real signal — it tests the WIRING, not IC sign."""
    px, mem = _fixtures(seed=2, n_sess=120)
    horizon, ns, emb, params = 5, 3, 5, {"n_estimators": 40}
    folds, ref = compute_shared_folds(px, mem, horizon, n_splits=ns, embargo_sessions=emb)

    base = run_arm_oos(px, pd.DataFrame(), mem, horizon, ["close"], "filed",
                      folds, ref, params)

    ref_dates = sorted(ref["date"].unique())
    ref_tickers = sorted(ref["ticker"].unique())
    sig_rows = [
        (d, t, float((i * 7 + j * 3) % 11))
        for i, d in enumerate(ref_dates)
        for j, t in enumerate(ref_tickers)
    ]
    sig_long = pd.DataFrame(sig_rows, columns=["date", "ticker", "sig"])

    # (a) sig IS consumed -> scores differ from base
    used = run_arm_oos(
        px, pd.DataFrame(), mem, horizon, ["close", "sig"], "filed",
        folds, ref, params, extra_features=sig_long,
    )
    used_s = used.set_index(["date", "ticker"])["score"]
    base_s = base.set_index(["date", "ticker"])["score"]
    common = used_s.index.intersection(base_s.index)
    assert not np.array_equal(
        used_s.loc[common].to_numpy(), base_s.loc[common].to_numpy()
    ), "sig in feature_cols did not change scores — column not consumed"

    # (b) sig present in the panel but NOT in feature_cols -> ignored -> bit-identical
    ignored = run_arm_oos(
        px, pd.DataFrame(), mem, horizon, ["close"], "filed",
        folds, ref, params, extra_features=sig_long,
    )
    ign_s = ignored.set_index(["date", "ticker"])["score"]
    common2 = ign_s.index.intersection(base_s.index)
    assert np.array_equal(
        ign_s.loc[common2].to_numpy(), base_s.loc[common2].to_numpy()
    ), "unused extra column leaked into the learner"


# ---------------------------------------------------------------------------
# E3 forward path: retain_unlabeled_from (round-56 fix)
# ---------------------------------------------------------------------------

def test_clean_panel_retains_forward_cross_section() -> None:
    """retain_unlabeled_from keeps the predict session's rows (NaN labels) —
    the entire point of forward prediction — while historical rows keep the
    realized-label-only drop semantics."""
    from aionis.eval.two_arm import _clean_panel

    px, mem = _fixtures(n_sess=40)
    predict_session = px.index[-1]  # the newest session: label unrealizable

    hist = _clean_panel(px, pd.DataFrame(), mem, 5, "filed")
    assert hist["date"].max() < predict_session, "historical dropna removes tail"

    fwd = _clean_panel(
        px, pd.DataFrame(), mem, 5, "filed",
        retain_unlabeled_from=predict_session,
    )
    tail = fwd[fwd["date"] == predict_session]
    assert len(tail) == 4  # all four tickers' forward cross-section retained
    assert tail["y_fwd_ret"].isna().all(), "forward labels are unknown by design"
    assert fwd["date"].max() == predict_session
    # historical section identical to the default behavior
    hist_part = fwd[fwd["date"] < predict_session].reset_index(drop=True)
    pd.testing.assert_frame_equal(hist_part, hist, check_exact=True)
