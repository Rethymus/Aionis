"""Memorization / point-in-time audit invariants.

``memorization_audit`` mirrors the estimand in ``compare.py`` (same
(event_id, symbol) pairing + parity guard, same event-date clustering) and
splits the per-cluster lift at the LLM cutoff. Tests pin parity, clustering,
the three interpretation regimes, the underpowered guard, y_true==0 neutrality,
and determinism. All frames are hand-built to match the OOS schema produced by
``evaluate.cross_validate`` (columns: event_id, symbol, y_true, group, <model>).

Each row carries a UNIQUE (event_id, symbol) — as real OOS frames do — so the
1:1 parity merge is well defined; clustering is by ``group`` (the event date),
so multiple rows may share a group to test cluster collapse.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from aionis.eval.pit_audit import memorization_audit

MODEL = "xgb"
SYM = "XLK"


def _arms(rows: list[tuple], model: str = MODEL) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build (price_oos, treat_oos) from (y_true, group, p_pred, t_pred).

    event_id is assigned uniquely per row so (event_id, symbol) is 1:1."""
    price_rows, treat_rows = [], []
    for i, (y, g, pp, tp) in enumerate(rows):
        eid = f"E{i}"
        price_rows.append({"event_id": eid, "symbol": SYM, "y_true": y, "group": g, model: pp})
        treat_rows.append({"event_id": eid, "symbol": SYM, model: tp})
    return pd.DataFrame(price_rows), pd.DataFrame(treat_rows)


PRE = [f"2020-{m:02d}-15" for m in range(1, 7)]   # 6 pre-cutoff clusters
POST = [f"2023-{m:02d}-15" for m in range(1, 7)]  # 6 post-cutoff clusters
CUTOFF = "2021-07-01"


# --- parity guard -------------------------------------------------------------


def test_asymmetric_arms_raise() -> None:
    price, treat = _arms([
        (1.0, "2020-01-15", -1.0, 1.0),
        (1.0, "2023-01-15", 1.0, 1.0),
    ])
    treat = treat.iloc[:-1]  # drop one row -> asymmetric
    with pytest.raises(RuntimeError, match="asymmetric"):
        memorization_audit(price, treat, MODEL, CUTOFF)


# --- clustering: same-date rows collapse to one cluster -----------------------


def test_same_date_rows_collapse_to_one_cluster() -> None:
    # Two rows on the SAME event date: one cluster, not two.
    rows = [
        (1.0, "2020-01-15", -1.0, 1.0),   # lift +1
        (-1.0, "2020-01-15", 1.0, -1.0),  # lift +1
    ] + [(1.0, d, 1.0, 1.0) for d in POST]  # neutral post clusters
    price, treat = _arms(rows)
    res = memorization_audit(price, treat, MODEL, CUTOFF)
    # The single 2020-01-15 cluster is the only pre cluster -> underpowered (<5),
    # but it must be ONE cluster (the two same-date rows averaged), not a crash.
    assert res["pre"]["n_clusters"] == 1
    assert res["pre"]["lift"] == pytest.approx(1.0)
    assert res["interpretation"] == "underpowered"


# --- memorization-consistent: lift only pre-cutoff ----------------------------


def test_memorization_consistent_when_lift_only_pre_cutoff() -> None:
    rows = [(1.0, d, -1.0, 1.0) for d in PRE]    # pre: t right, p wrong -> lift +1
    rows += [(1.0, d, 1.0, 1.0) for d in POST]   # post: both right -> lift 0
    price, treat = _arms(rows)
    res = memorization_audit(price, treat, MODEL, CUTOFF)
    assert res["pre"]["lift"] == pytest.approx(1.0)
    assert res["post"]["lift"] == pytest.approx(0.0)
    assert res["gap"] == pytest.approx(1.0)
    assert res["gap_ci"][0] > 0
    assert res["interpretation"] == "memorization-consistent"


# --- no-memorization-signal: symmetric skill across eras ----------------------


def test_no_memorization_signal_when_lift_symmetric() -> None:
    # Alternating +1/-1 cluster lifts, identical in both eras -> mean 0, gap 0.
    # Row giving lift +1: y=1, p wrong(-1), t right(1). Lift -1: y=1, p right(1), t wrong(-1).
    pattern = [(-1.0, 1.0), (1.0, -1.0)] * 3
    rows = [(1.0, d, pp, tp) for d, (pp, tp) in zip(PRE, pattern, strict=True)]
    rows += [(1.0, d, pp, tp) for d, (pp, tp) in zip(POST, pattern, strict=True)]
    price, treat = _arms(rows)
    res = memorization_audit(price, treat, MODEL, CUTOFF)
    assert res["gap"] == pytest.approx(0.0, abs=1e-9)
    assert res["gap_ci"][0] <= 0 <= res["gap_ci"][1]
    assert res["interpretation"] == "no-memorization-signal"


def test_post_stronger_when_lift_only_post_cutoff() -> None:
    rows = [(1.0, d, 1.0, 1.0) for d in PRE]     # pre: both right -> lift 0
    rows += [(1.0, d, -1.0, 1.0) for d in POST]  # post: lift +1
    price, treat = _arms(rows)
    res = memorization_audit(price, treat, MODEL, CUTOFF)
    assert res["gap"] == pytest.approx(-1.0)
    assert res["gap_ci"][1] < 0
    assert res["interpretation"] == "post-stronger"


# --- underpowered guard -------------------------------------------------------


def test_underpowered_when_too_few_pre_clusters() -> None:
    few_pre = [f"2020-0{m}-15" for m in range(1, 4)]  # only 3 pre clusters (< 5)
    rows = [(1.0, d, -1.0, 1.0) for d in few_pre]
    rows += [(1.0, d, 1.0, 1.0) for d in POST]
    price, treat = _arms(rows)
    res = memorization_audit(price, treat, MODEL, CUTOFF)
    assert res["interpretation"] == "underpowered"
    assert math.isnan(res["gap_ci"][0]) and math.isnan(res["gap_ci"][1])
    assert res["pre"]["n_clusters"] == 3


# --- y_true == 0 rows are neutral (no spurious hit either way) -----------------


def test_zero_true_return_rows_are_neutral() -> None:
    # All-zero cluster: no direction -> lift 0 for every row, no crash, no signal.
    rows = [(0.0, d, 1.0, 1.0) for d in PRE]
    rows += [(1.0, d, 1.0, 1.0) for d in POST]
    price, treat = _arms(rows)
    res = memorization_audit(price, treat, MODEL, CUTOFF)
    assert res["pre"]["lift"] == pytest.approx(0.0)


def test_zero_true_return_rows_dilute_but_do_not_invent_lift() -> None:
    # A mixed cluster: one y!=0 row (lift +1) + one y==0 row (neutral lift 0).
    # Per-cluster lift is the row mean -> 0.5, not 1.0 (zero rows count as non-hits,
    # consistent with metrics.directional_accuracy).
    rows = [
        (1.0, "2020-01-15", -1.0, 1.0),
        (0.0, "2020-01-15", 1.0, 1.0),
    ] + [(1.0, d, 1.0, 1.0) for d in POST]
    price, treat = _arms(rows)
    res = memorization_audit(price, treat, MODEL, CUTOFF)
    assert res["pre"]["lift"] == pytest.approx(0.5)


# --- determinism --------------------------------------------------------------


def test_deterministic_under_fixed_seed() -> None:
    rng = np.random.default_rng(9)
    rows = []
    for d in PRE + POST:
        y = float(rng.choice([-1.0, 1.0]))
        rows.append((y, d, float(rng.choice([-1.0, 1.0])), float(rng.choice([-1.0, 1.0]))))
    price, treat = _arms(rows)
    r1 = memorization_audit(price, treat, MODEL, CUTOFF, seed=11)
    r2 = memorization_audit(price, treat, MODEL, CUTOFF, seed=11)
    assert r1 == r2
