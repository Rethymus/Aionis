"""VIX surprise transform invariants — hermetic (no network).

Pins :mod:`aionis.features.vix_surprise`: ΔVIX correctness + PIT; the AR residual
is ~0 on a perfectly-AR series and large on a shock; the surprise is strictly
point-in-time (a future shock cannot move a past surprise — the critical test,
mirrors ``test_macro_surprise.py``); deterministic; and the warmup rows are NaN
(no leak through imputation). The panel convenience is exercised with
``vix_as_of`` stubbed so no fetch occurs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.features.vix_surprise import (
    AR_LAGS,
    AR_WINDOW,
    Z_CLIP,
    _ar_residuals,
    vix_ar_surprise,
    vix_delta,
    vix_surprise_panel,
)


def _ar_series(
    n: int,
    phi: tuple[float, ...],
    seed: int,
    *,
    noise: float = 0.0,
    start: float = 15.0,
) -> pd.Series:
    """Deterministic AR(len(phi)) series on a business-day calendar.

    ``noise=0`` → an exact AR process (used to pin residual ~0 on a correct fit).
    """
    rng = np.random.default_rng(seed)
    p = len(phi)
    vals = np.empty(n, dtype=float)
    vals[:p] = start
    for i in range(p, n):
        v = sum(phi[k] * vals[i - 1 - k] for k in range(p))
        vals[i] = v + noise * float(rng.standard_normal())
    idx = pd.DatetimeIndex(pd.date_range("2022-01-03", periods=n, freq="B"))
    s = pd.Series(vals, index=idx, name="vix")
    s.index.name = "date"
    return s


# --- vix_delta -----------------------------------------------------------------


def test_delta_correctness_default_lag() -> None:
    s = pd.Series([10.0, 12.0, 11.0, 15.0], index=pd.date_range("2024-01-02", periods=4))

    d = vix_delta(s)

    assert d.name == "vix_delta"
    assert pd.isna(d.iloc[0])
    assert d.iloc[1] == pytest.approx(2.0)
    assert d.iloc[2] == pytest.approx(-1.0)
    assert d.iloc[3] == pytest.approx(4.0)


def test_delta_respects_lag_parameter() -> None:
    s = pd.Series([10.0, 12.0, 11.0, 15.0], index=pd.date_range("2024-01-02", periods=4))

    d = vix_delta(s, lag=2)

    assert pd.isna(d.iloc[0])
    assert pd.isna(d.iloc[1])
    assert d.iloc[2] == pytest.approx(1.0)  # 11 - 10
    assert d.iloc[3] == pytest.approx(3.0)  # 15 - 12


def test_delta_is_point_in_time() -> None:
    """A future value cannot move a past ΔVIX."""
    base = _ar_series(40, (0.5, 0.2), seed=1)
    shocked = base.copy()
    shocked.iloc[30] += 25.0  # shock at 30

    d_base = vix_delta(base)
    d_shocked = vix_delta(shocked)

    pd.testing.assert_series_equal(d_base.iloc[:30], d_shocked.iloc[:30])
    assert d_shocked.iloc[30] == pytest.approx(d_base.iloc[30] + 25.0)  # the shock shows up at 30
    assert d_shocked.iloc[31] == pytest.approx(d_base.iloc[31] - 25.0)  # and reverts at 31


def test_delta_nan_warmup() -> None:
    s = _ar_series(10, (0.5,), seed=2)

    d = vix_delta(s, lag=3)

    assert d.iloc[:3].isna().all()
    assert d.iloc[3:].notna().all()


# --- _ar_residuals + vix_ar_surprise -------------------------------------------


def test_ar_residual_near_zero_on_perfect_ar() -> None:
    """A correctly-specified AR fit on noise-free AR data recovers the process —
    residuals are at machine precision (the level, not the standardized surprise)."""
    s = _ar_series(80, (0.5, 0.3), seed=3, noise=0.0)  # exact AR(2)
    resid = _ar_residuals(s, window=AR_WINDOW, ar_lags=2)

    assert resid.name == "vix_ar_resid"
    assert resid.iloc[:AR_WINDOW].isna().all()  # warmup
    assert resid.dropna().abs().max() < 1e-6


def test_ar_residual_large_on_shock_and_pit() -> None:
    """A shock at t produces a large residual at t, and residuals strictly before t
    are unchanged (the shock is the only new information at t)."""
    base = _ar_series(80, (0.5, 0.3), seed=4, noise=0.05)
    shocked = base.copy()
    t = 50
    shocked.iloc[t] += 25.0

    r_base = _ar_residuals(base, window=AR_WINDOW, ar_lags=2)
    r_shocked = _ar_residuals(shocked, window=AR_WINDOW, ar_lags=2)

    pd.testing.assert_series_equal(r_base.iloc[:t], r_shocked.iloc[:t])  # PIT: past unchanged
    assert abs(r_shocked.iloc[t]) > 10.0  # the shock is the surprise
    assert r_shocked.iloc[t] != pytest.approx(r_base.iloc[t])


def test_ar_surprise_no_lookahead() -> None:
    """The critical PIT test (mirrors macro_surprise): grossly perturbing every VIX
    value dated >= T must leave the surprise at every date < T unchanged."""
    base = _ar_series(90, (0.5, 0.3, 0.1), seed=5, noise=0.1)
    z_base = vix_ar_surprise(base, window=AR_WINDOW, ar_lags=AR_LAGS)
    T = 50
    assert not pd.isna(z_base.iloc[T - 1])  # the surprise is defined at T-1

    future = base.copy()
    future.iloc[T:] = future.iloc[T:].to_numpy() * 3.0 + 40.0  # scramble everything >= T
    z_future = vix_ar_surprise(future, window=AR_WINDOW, ar_lags=AR_LAGS)

    pd.testing.assert_series_equal(z_base.iloc[:T], z_future.iloc[:T])


def test_ar_surprise_deterministic() -> None:
    s = _ar_series(80, (0.5, 0.3), seed=6, noise=0.1)

    a = vix_ar_surprise(s)
    b = vix_ar_surprise(s)

    pd.testing.assert_series_equal(a, b)


def test_ar_surprise_nan_warmup_and_clipped() -> None:
    s = _ar_series(80, (0.5, 0.3), seed=7, noise=0.3)
    z = vix_ar_surprise(s, window=AR_WINDOW, ar_lags=AR_LAGS)

    assert z.name == "vix_ar_surprise"
    assert z.iloc[:AR_WINDOW].isna().all()  # at least the first `window` rows are NaN
    assert z.notna().any()  # ...and the rest is populated (not all-NaN)
    assert z.dropna().abs().max() <= Z_CLIP  # surprise is clipped


# --- vix_surprise_panel (vix_as_of stubbed — hermetic) --------------------------


def _stub_vix_as_of(monkeypatch: pytest.MonkeyPatch, series: pd.Series) -> None:
    monkeypatch.setattr(
        "aionis.features.vix_surprise.vix_as_of", lambda dates, **kw: series
    )


def test_panel_ar_kind_aligns_to_dates(monkeypatch: pytest.MonkeyPatch) -> None:
    vix = _ar_series(80, (0.5, 0.3), seed=8, noise=0.1)
    dates = pd.DatetimeIndex(vix.index)
    _stub_vix_as_of(monkeypatch, vix)

    panel = vix_surprise_panel(dates, kind="ar")

    assert panel.name == "vix_ar_surprise"
    assert list(panel.index) == list(pd.DatetimeIndex(dates).normalize())
    pd.testing.assert_series_equal(panel, vix_ar_surprise(vix).reindex(dates.normalize()))


def test_panel_delta_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    dates = pd.DatetimeIndex(pd.date_range("2022-01-03", periods=10, freq="B"))
    vix = pd.Series(np.arange(10.0) + 10.0, index=dates, name="vix")
    _stub_vix_as_of(monkeypatch, vix)

    panel = vix_surprise_panel(dates, kind="delta")

    assert panel.name == "vix_delta"
    assert list(panel.index) == list(dates)
    assert panel.iloc[1] == pytest.approx(1.0)


def test_panel_invalid_kind_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    dates = pd.DatetimeIndex(pd.date_range("2022-01-03", periods=5, freq="B"))
    vix = pd.Series([15.0] * 5, index=dates, name="vix")
    _stub_vix_as_of(monkeypatch, vix)

    with pytest.raises(ValueError, match="unknown kind"):
        vix_surprise_panel(dates, kind="bogus")
