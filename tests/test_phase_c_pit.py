"""Joined-panel PIT test (phase-c-preregistration §5 #4 / §8.0 item #1) — hermetic.

The component transforms (macro-surprise broadcast, VIX-surprise, earnings-surprise
as-of) each carry their own PIT tests. This is the GLUE test: when those features
are assembled into one panel by :func:`build_selection_panel` via the ``macro=``
and ``extra_features=`` paths, a value first published at date ``r`` must NOT
appear at any panel date ``d < r`` (no forward-fill, no cross-date propagation in
the join). It would catch a regression where someone added an ``.ffill()`` to the
glue or keyed the merge on the wrong column.
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
    """The exact NYSE trading-day grid ``build_selection_panel`` reindexes to
    (drops holidays that ``bdate_range`` includes)."""
    return list(nyse_sessions(px.index.min(), px.index.max()))


def test_macro_release_does_not_leak_to_earlier_panel_dates() -> None:
    """A macro surprise first published at ``r`` is present ONLY at panel rows with
    date >= r (when the caller pre-broadcasts it as a step function) and NEVER at
    d < r. The glue must not forward-fill a sparse frame either (next test)."""
    px = _px()
    sessions = _sessions(px)
    r = sessions[10]  # release date
    C = 0.7
    # PIT step function: NaN strictly before r, C from r onward (what
    # macro_surprise_date_broadcast produces — knowable at d >= r only)
    macro = pd.DataFrame(
        {"macro_x": [np.nan if d < r else C for d in sessions]},
        index=pd.DatetimeIndex(sessions),
    )

    panel = build_selection_panel(px, pd.DataFrame(), horizon=1, macro=macro)

    by_date = panel.groupby("date")["macro_x"].first()
    for d in sessions:
        if d < r:
            assert pd.isna(by_date.loc[d]), f"macro leaked to {d} (< release {r})"
        else:
            assert by_date.loc[d] == C, f"macro missing/wrong at {d} (>= release {r})"


def test_glue_does_not_forward_fill_a_sparse_macro() -> None:
    """If the caller passes a SPARSE macro (value only at the release date, NaN
    elsewhere), the glue must NOT propagate it — it stays present only at that
    date. (Carry-forward is the caller's job via ``macro_surprise_date_broadcast``;
    the panel join itself is exact-date.)"""
    px = _px()
    sessions = _sessions(px)
    r = sessions[8]
    sparse = pd.DataFrame(
        {"macro_x": [C if d == r else np.nan for d in sessions for C in (0.5,)]},
        index=pd.DatetimeIndex(sessions),
    )

    panel = build_selection_panel(px, pd.DataFrame(), horizon=1, macro=sparse)

    by_date = panel.groupby("date")["macro_x"].first()
    assert by_date.loc[r] == 0.5
    leaked = [d for d in sessions if d != r and not pd.isna(by_date.loc[d])]
    assert leaked == [], f"glue forward-filled macro to {leaked}"


def test_earnings_filed_at_F_visible_only_from_F_per_ticker() -> None:
    """Ticker A's earnings surprise (filed at F) is visible at panel rows with
    date >= F for A only; ticker B (no filing) is always NaN. The per-(ticker,
    date) join must not smear a value across tickers or to earlier dates."""
    px = _px()
    sessions = _sessions(px)
    F = sessions[12]
    V = 1.3
    # extra_features: A has V at every date >= F (the as-of broadcast), NaN before;
    # B never appears (all NaN).
    rows = []
    for d in sessions:
        rows.append((d, "A", V if d >= F else np.nan))
    earn = pd.DataFrame(rows, columns=["date", "ticker", "earnings_surprise"])

    panel = build_selection_panel(
        px, pd.DataFrame(), horizon=1, extra_features=earn,
    )
    a = panel[panel["ticker"] == "A"].set_index("date")["earnings_surprise"]
    b = panel[panel["ticker"] == "B"].set_index("date")["earnings_surprise"]

    for d in sessions:
        if d < F:
            assert pd.isna(a.loc[d]), f"A's earnings leaked to {d} (< filing {F})"
        else:
            assert a.loc[d] == V, f"A's earnings missing at {d} (>= filing {F})"
    # B never has earnings -> always NaN (no cross-ticker smear)
    assert b.isna().all()
