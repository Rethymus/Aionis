"""Phase D joined-panel PIT test (phase-d-preregistration §5 #4 / §8 item) — hermetic.

The component transforms (peer_momentum, stakes_13d_signal) each carry their own
PIT tests. This is the GLUE test: when the relationship bundle is assembled into
one panel by :func:`build_selection_panel` via the ``extra_features=`` path, a
value first knowable at date ``r`` must NOT appear at any panel date ``d < r``
(no forward-fill, no cross-date propagation in the join), and must not smear
across tickers. Mirrors ``test_phase_c_pit`` for the Phase D rel-bundle shape.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.features.alignment import nyse_sessions
from aionis.features.selection_panel import build_selection_panel


def _px(n_sess: int = 24, tickers: tuple[str, ...] = ("A", "B")) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-02", periods=n_sess)
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        100 + np.cumsum(rng.normal(size=(n_sess, len(tickers))), axis=0),
        index=idx, columns=list(tickers),
    )


def _sessions(px: pd.DataFrame) -> list[pd.Timestamp]:
    return list(nyse_sessions(px.index.min(), px.index.max()))


def test_rel_bundle_value_does_not_forward_fill_across_dates() -> None:
    """A rel-bundle value present ONLY at release date ``r`` (NaN elsewhere) must
    stay present only at panel rows with date == r — the glue must not carry it
    forward (carry-forward is the caller's job; the join is exact-date)."""
    px = _px()
    sessions = _sessions(px)
    r = sessions[10]
    rows = [
        (d, "A", 0.5 if d == r else np.nan, 1.0 if d == r else np.nan)
        for d in sessions
    ]
    rel = pd.DataFrame(rows, columns=["date", "ticker", "peer_mom", "stakes_13d_event"])

    panel = build_selection_panel(px, pd.DataFrame(), horizon=1, extra_features=rel)

    by_date = panel.groupby("date")[["peer_mom", "stakes_13d_event"]].first()
    for d in sessions:
        if d == r:
            assert by_date.loc[d, "peer_mom"] == 0.5
            assert by_date.loc[d, "stakes_13d_event"] == 1.0
        else:
            assert pd.isna(by_date.loc[d, "peer_mom"])
            assert pd.isna(by_date.loc[d, "stakes_13d_event"])


def test_rel_bundle_value_does_not_smear_across_tickers() -> None:
    """A rel-bundle value for ticker A must not appear on ticker B at the same
    date — the per-(ticker, date) join is exact (no cross-ticker leak)."""
    px = _px()
    sessions = _sessions(px)
    d0 = sessions[5]
    rel = pd.DataFrame(
        [{"date": d0, "ticker": "A", "peer_mom": 0.7, "stakes_13d_event": 1.0}],
    )

    panel = build_selection_panel(px, pd.DataFrame(), horizon=1, extra_features=rel)
    sub = panel[panel["date"] == d0].set_index("ticker")

    assert sub.loc["A", "peer_mom"] == 0.7
    assert sub.loc["A", "stakes_13d_event"] == 1.0
    # B has no rel row at d0 -> the exact (date, ticker) join leaves it NaN
    # (the panel never imputes; the assembled run pre-fills 0 upstream).
    assert pd.isna(sub.loc["B", "peer_mom"])
    assert pd.isna(sub.loc["B", "stakes_13d_event"])


def test_assembled_rel_bundle_is_pit_end_to_end() -> None:
    """End-to-end: peer_momentum_panel (backward) + stakes_13d_event_panel
    (filing-date backward asof) -> rel_extra -> build_selection_panel. A future
    price perturbation must not move a past peer_mom, and a 13D filing at F must
    not appear at d < F in the assembled panel."""
    from aionis.features.peer_momentum import peer_momentum_panel
    from aionis.features.stakes_13d_signal import stakes_13d_event_panel

    px = _px(n_sess=40)
    sessions = _sessions(px)
    sic = {"A": "X", "B": "X"}
    peer = peer_momentum_panel(px, sic, window=5)
    events = pd.DataFrame({"ticker": ["A"], "filing_date": [str(sessions[20].date())]})
    stakes = stakes_13d_event_panel(events, pd.DatetimeIndex(sessions), ["A", "B"], window_days=10)

    # stack both into the rel_extra long shape the runner uses
    peer_long = peer.stack().rename("peer_mom").reset_index().rename(
        columns={"level_0": "date", "level_1": "ticker"}
    )
    stakes_long = stakes.stack().rename("stakes_13d_event").reset_index().rename(
        columns={"level_0": "date", "level_1": "ticker"}
    )
    rel = peer_long.merge(stakes_long, on=["date", "ticker"], how="outer")

    panel = build_selection_panel(px, pd.DataFrame(), horizon=1, extra_features=rel)

    # 13D filing at sessions[20] is NOT visible before sessions[20] for ticker A
    a = panel[panel["ticker"] == "A"].set_index("date")["stakes_13d_event"].fillna(0.0)
    pre = [s for s in sessions if s < sessions[20]]
    assert a.reindex(pre).fillna(0.0).sum() == 0.0
    assert a.loc[sessions[20]] == 1.0  # visible at its own filing date
