"""Earnings-surprise invariants — hermetic (no network).

Pins the naive seasonal-random-walk expectation and the filing-date PIT
discipline of :mod:`aionis.features.earnings_surprise`:

  * EPS actual = net_income / shares_out (NaN where shares <= 0);
  * naive expected = same-quarter-prior-year EPS (q-4); NaN before q-4 history;
  * surprise sign/magnitude on a known EPS jump (the whole point of the feature);
  * PIT anchor on ``filed``: a surprise filed at F is visible at d >= F and
    NEVER at d < F (mirrors ``test_fundamentals.py`` / ``test_vix.py``);
  * z-score uses ONLY strictly-prior surprises (shift(1) before expanding);
  * determinism.

Synthetic frames only — no EDGAR, no FRED.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.features.earnings_surprise import (
    Z_CLIP,
    earnings_surprise_as_of,
    earnings_surprise_long,
)

# --- fixture builders --------------------------------------------------------
# Calendar quarters; 10-Q ~45d after end, 10-K ~55d (form-dependent lag mirrors
# real EDGAR cadence and keeps filing dates strictly period-ordered).
_QUARTERS = [
    ("2023-03-31", 2023, "Q1", "10-Q", 45),
    ("2023-06-30", 2023, "Q2", "10-Q", 45),
    ("2023-09-30", 2023, "Q3", "10-Q", 45),
    ("2023-12-31", 2023, "FY", "10-K", 55),
    ("2024-03-31", 2024, "Q1", "10-Q", 45),
    ("2024-06-30", 2024, "Q2", "10-Q", 45),
    ("2024-09-30", 2024, "Q3", "10-Q", 45),
    ("2024-12-31", 2024, "FY", "10-K", 55),
    ("2025-03-31", 2025, "Q1", "10-Q", 45),
    ("2025-06-30", 2025, "Q2", "10-Q", 45),
]


def _filed(end: str, form: str, lag: int) -> str:
    return (pd.Timestamp(end) + pd.Timedelta(days=lag)).strftime("%Y-%m-%d")


def _build_long(
    net_income: dict[str, list[float]],
    shares: dict[str, float],
    n_quarters: int,
    *,
    share_override: dict[str, dict[int, float]] | None = None,
) -> pd.DataFrame:
    """Synthetic fundamentals long-frame shaped like build_fundamentals output.

    ``net_income``: {ticker: [ni_q1, ni_q2, ...]} (len == n_quarters).
    ``shares``: {ticker: constant shares_out} unless overridden per quarter.
    """
    rows: list[dict] = []
    share_override = share_override or {}
    for ticker, nis in net_income.items():
        assert len(nis) >= n_quarters, f"{ticker} needs {n_quarters} net_income values"
        for i, (end, fy, fp, form, lag) in enumerate(_QUARTERS[:n_quarters]):
            filed = _filed(end, form, lag)
            sh = share_override.get(ticker, {}).get(i, shares[ticker])
            rows.append(
                {
                    "ticker": ticker,
                    "metric": "net_income",
                    "end": end,
                    "filed": filed,
                    "form": form,
                    "fy": fy,
                    "fp": fp,
                    "value": float(nis[i]),
                    "unit": "USD",
                }
            )
            rows.append(
                {
                    "ticker": ticker,
                    "metric": "shares_out",
                    "end": end,
                    "filed": filed,
                    "form": form,
                    "fy": fy,
                    "fp": fp,
                    "value": float(sh),
                    "unit": "shares",
                }
            )
    return pd.DataFrame(rows)


def _row(out: pd.DataFrame, ticker: str, end: str) -> pd.Series:
    r = out[(out["ticker"] == ticker) & (out["end"] == end)]
    assert len(r) == 1, f"expected one row for {ticker} {end}, got {len(r)}"
    return r.iloc[0]


# --- EPS actual --------------------------------------------------------------


def test_eps_actual_is_net_income_over_shares() -> None:
    # shares=100 -> EPS = ni/100 exactly.
    long = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0]},
        {"AAA": 100.0},
        n_quarters=6,
    )
    out = earnings_surprise_long(long)
    assert _row(out, "AAA", "2024-03-31")["eps_actual"] == pytest.approx(0.50)  # jump
    assert _row(out, "AAA", "2023-12-31")["eps_actual"] == pytest.approx(0.14)
    assert _row(out, "AAA", "2023-03-31")["eps_actual"] == pytest.approx(0.10)


def test_eps_actual_nan_where_shares_non_positive() -> None:
    # Zero / negative share count is not a meaningful EPS basis -> NaN there, but
    # the same firm's healthy quarters still compute.
    long = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0]},
        {"AAA": 100.0},
        n_quarters=6,
        share_override={"AAA": {2: 0.0, 4: -5.0}},  # q3 zero, q5 negative
    )
    out = earnings_surprise_long(long)
    assert pd.isna(_row(out, "AAA", "2023-09-30")["eps_actual"])  # shares == 0
    assert pd.isna(_row(out, "AAA", "2024-03-31")["eps_actual"])  # shares < 0
    assert _row(out, "AAA", "2023-06-30")["eps_actual"] == pytest.approx(0.12)


# --- naive q-4 expectation ---------------------------------------------------


def test_naive_expected_is_same_quarter_prior_year_eps() -> None:
    long = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0]},
        {"AAA": 100.0},
        n_quarters=6,
    )
    out = earnings_surprise_long(long)
    # q5 expected = q1 EPS (0.10); q6 expected = q2 EPS (0.12).
    assert _row(out, "AAA", "2024-03-31")["eps_expected"] == pytest.approx(0.10)
    assert _row(out, "AAA", "2024-06-30")["eps_expected"] == pytest.approx(0.12)


def test_naive_expected_nan_before_q4_history() -> None:
    # The first four quarters have no prior-year-quarter filing -> no expectation,
    # no surprise (the honest "can't compute a seasonal walk yet" signal).
    long = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0]},
        {"AAA": 100.0},
        n_quarters=6,
    )
    out = earnings_surprise_long(long)
    for end in ("2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31"):
        r = _row(out, "AAA", end)
        assert pd.isna(r["eps_expected"]), end
        assert pd.isna(r["surprise"]), end


# --- surprise sign / magnitude on the jump -----------------------------------


def test_surprise_sign_and_magnitude_on_jump() -> None:
    # q5 net_income jumps 10 -> 50 (EPS 0.10 -> 0.50); naive expected stays q1's
    # 0.10. Relative surprise = (0.50 - 0.10) / |0.10| = +4.0 (large, positive).
    long = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0]},
        {"AAA": 100.0},
        n_quarters=6,
    )
    out = earnings_surprise_long(long)
    jump = _row(out, "AAA", "2024-03-31")
    assert jump["surprise"] == pytest.approx(4.0)
    assert jump["surprise"] > 0.0  # an upside surprise


def test_surprise_negative_when_actual_below_prior_year() -> None:
    # EPS falls vs the same quarter last year -> negative surprise.
    long = _build_long(
        {"BBB": [40.0, 40.0, 40.0, 40.0, 20.0, 40.0]},
        {"BBB": 100.0},
        n_quarters=6,
    )
    out = earnings_surprise_long(long)
    miss = _row(out, "BBB", "2024-03-31")  # actual 0.20 vs expected 0.40
    assert miss["surprise"] == pytest.approx(-0.5)
    assert miss["surprise"] < 0.0


def test_surprise_nan_when_expected_zero() -> None:
    # If the q-4 EPS basis is exactly 0 the relative surprise is undefined.
    long = _build_long(
        {"AAA": [0.0, 12.0, 11.0, 14.0, 50.0, 0.0]},
        {"AAA": 100.0},
        n_quarters=6,
    )
    out = earnings_surprise_long(long)
    # q5 expected = q1 EPS = 0.0 -> surprise NaN (not inf).
    assert _row(out, "AAA", "2024-03-31")["eps_expected"] == pytest.approx(0.0)
    assert pd.isna(_row(out, "AAA", "2024-03-31")["surprise"])


# --- per-ticker isolation ----------------------------------------------------


def test_expectation_and_z_are_isolated_per_ticker() -> None:
    # Two tickers with different EPS paths; q-4 matching must not cross tickers.
    long = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0], "BBB": [40.0, 40.0, 40.0, 40.0, 20.0, 40.0]},
        {"AAA": 100.0, "BBB": 200.0},
        n_quarters=6,
    )
    out = earnings_surprise_long(long)
    assert _row(out, "AAA", "2024-03-31")["eps_expected"] == pytest.approx(0.10)  # q1 AAA
    assert _row(out, "BBB", "2024-03-31")["eps_expected"] == pytest.approx(0.20)  # q1 BBB
    assert set(out["ticker"].unique()) == {"AAA", "BBB"}


# --- z-score uses only strictly-prior surprises -------------------------------


def test_zscore_hand_matches_expanding_over_strictly_prior() -> None:
    # With >= 2 prior surprises (from q5, q6), q7's z is finite and equals the
    # hand computation over ONLY q5/q6 surprises (ddof=1).
    long = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0, 12.0, 15.0]},
        {"AAA": 100.0},
        n_quarters=8,
    )
    out = earnings_surprise_long(long)
    s_q5 = _row(out, "AAA", "2024-03-31")["surprise"]
    s_q6 = _row(out, "AAA", "2024-06-30")["surprise"]
    s_q7 = _row(out, "AAA", "2024-09-30")["surprise"]
    prior = np.array([s_q5, s_q6], dtype=float)
    mu = prior.mean()
    sigma = prior.std(ddof=1)
    expected_z = float(np.clip((s_q7 - mu) / sigma, -Z_CLIP, Z_CLIP))
    assert _row(out, "AAA", "2024-09-30")["surprise_z"] == pytest.approx(expected_z)
    # And it is NOT NaN once enough history exists.
    assert pd.notna(_row(out, "AAA", "2024-09-30")["surprise_z"])


def test_zscore_uses_only_past_future_perturbation_invariant() -> None:
    # Perturb the LAST quarter's EPS and recompute: every z filed BEFORE that
    # quarter is byte-identical (no future leakage into past z's). Only the
    # perturbed quarter's own z may move. This is the PIT invariant on the z side.
    base = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0, 12.0, 15.0, 14.0, 16.0]},
        {"AAA": 100.0},
        n_quarters=10,
    )
    out_base = earnings_surprise_long(base)
    # q10 net_income 16 -> 9999 (a huge late surprise).
    pert = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0, 12.0, 15.0, 14.0, 9999.0]},
        {"AAA": 100.0},
        n_quarters=10,
    )
    out_pert = earnings_surprise_long(pert)

    pre = out_base[out_base["end"] != "2025-06-30"].reset_index(drop=True)
    pre_p = out_pert[out_pert["end"] != "2025-06-30"].reset_index(drop=True)
    pd.testing.assert_series_equal(
        pre["surprise_z"],
        pre_p["surprise_z"],
        check_names=False,
        check_index=False,
    )
    # The perturbed quarter's z itself is allowed to change (it is the new value).
    assert not np.isclose(
        _row(out_base, "AAA", "2025-06-30")["surprise_z"],
        _row(out_pert, "AAA", "2025-06-30")["surprise_z"],
        equal_nan=True,
    )


def test_zscore_nan_until_two_strictly_prior_surprises() -> None:
    # ddof=1 std needs >= 2 strictly-prior surprises: q5 (0 prior) and q6 (1
    # prior) -> z NaN; q7 (2 prior) -> finite.
    long = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0, 12.0, 15.0]},
        {"AAA": 100.0},
        n_quarters=8,
    )
    out = earnings_surprise_long(long)
    assert pd.isna(_row(out, "AAA", "2024-03-31")["surprise_z"])  # 0 prior
    assert pd.isna(_row(out, "AAA", "2024-06-30")["surprise_z"])  # 1 prior
    assert pd.notna(_row(out, "AAA", "2024-09-30")["surprise_z"])  # 2 prior


def test_zscore_clipped_to_cap() -> None:
    # An extreme outlier surprise is clipped to +/- Z_CLIP (fat-tail discipline).
    long = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0, 12.0, 15.0, 14.0, 99999.0]},
        {"AAA": 100.0},
        n_quarters=10,
    )
    out = earnings_surprise_long(long)
    z = _row(out, "AAA", "2025-06-30")["surprise_z"]
    assert pd.notna(z)
    assert -Z_CLIP <= z <= Z_CLIP


# --- PIT anchor on `filed` (the as_of join) ----------------------------------


def test_as_of_surprise_not_visible_before_its_filing_date() -> None:
    # A surprise whose FILING is F is visible at d == F but NOT at d == F-1.
    # (surprise_z first finite at q7: >= 2 prior surprises q5/q6.)
    long = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0, 12.0, 15.0]},
        {"AAA": 100.0},
        n_quarters=8,
    )
    out = earnings_surprise_long(long)
    filed_q7 = pd.Timestamp(_row(out, "AAA", "2024-09-30")["filed"])
    z_q7 = _row(out, "AAA", "2024-09-30")["surprise_z"]
    assert pd.notna(z_q7)

    dates = pd.DatetimeIndex(
        [filed_q7 - pd.Timedelta(days=1), filed_q7, filed_q7 + pd.Timedelta(days=30)]
    ).normalize()
    wide = earnings_surprise_as_of(out, dates, ["AAA"])

    assert pd.isna(wide.loc[filed_q7 - pd.Timedelta(days=1), "AAA"])  # NOT yet filed
    assert wide.loc[filed_q7, "AAA"] == pytest.approx(z_q7)  # filed -> visible
    assert wide.loc[filed_q7 + pd.Timedelta(days=30), "AAA"] == pytest.approx(z_q7)  # carried


def test_as_of_nan_before_first_filing() -> None:
    # Before a ticker's first filing, no surprise is knowable -> NaN.
    long = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0]},
        {"AAA": 100.0},
        n_quarters=6,
    )
    out = earnings_surprise_long(long)
    first_filed = pd.Timestamp(out["filed"].min())
    dates = pd.DatetimeIndex([first_filed - pd.Timedelta(days=1), first_filed]).normalize()
    wide = earnings_surprise_as_of(out, dates, ["AAA"])
    assert pd.isna(wide.loc[first_filed - pd.Timedelta(days=1), "AAA"])


def test_as_of_pit_anchored_on_filed_not_end() -> None:
    # The same period-end value is NOT visible before its filing: between
    # period-end and filing the surprise must be NaN (the lookahead guard).
    long = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0, 12.0, 15.0]},
        {"AAA": 100.0},
        n_quarters=8,
    )
    out = earnings_surprise_long(long)
    filed_q7 = pd.Timestamp(_row(out, "AAA", "2024-09-30")["filed"])
    end_q7 = pd.Timestamp("2024-09-30")
    # end_q7 < filed_q7 by construction (45d lag): at end_q7 the q7 surprise is
    # NOT yet filed, so the latest knowable surprise_z is still q6's (which is
    # NaN — z needs >=2 prior) -> NaN; only at filed_q7 does q7's z appear.
    assert end_q7 < filed_q7
    dates = pd.DatetimeIndex([end_q7, filed_q7]).normalize()
    wide = earnings_surprise_as_of(out, dates, ["AAA"])
    assert pd.isna(wide.loc[end_q7, "AAA"])  # period-end: not filed yet
    assert pd.notna(wide.loc[filed_q7, "AAA"])  # filing date: now visible


def test_as_of_carries_forward_latest_knowable() -> None:
    # Between two filings, the earlier surprise_z persists (backward asof).
    long = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0, 12.0, 15.0]},
        {"AAA": 100.0},
        n_quarters=8,
    )
    out = earnings_surprise_long(long)
    f7 = pd.Timestamp(_row(out, "AAA", "2024-09-30")["filed"])
    f8 = pd.Timestamp(_row(out, "AAA", "2024-12-31")["filed"])
    z7 = _row(out, "AAA", "2024-09-30")["surprise_z"]
    z8 = _row(out, "AAA", "2024-12-31")["surprise_z"]
    mid = f7 + (f8 - f7) / 2
    wide = earnings_surprise_as_of(out, pd.DatetimeIndex([f7, mid, f8]).normalize(), ["AAA"])
    assert wide.loc[f7, "AAA"] == pytest.approx(z7)
    assert wide.loc[mid, "AAA"] == pytest.approx(z7)  # q7 z carries until q8 filed
    assert wide.loc[f8, "AAA"] == pytest.approx(z8)  # then q8 z takes over


# --- determinism + degenerate inputs -----------------------------------------


def test_determinism_two_runs_identical() -> None:
    long = _build_long(
        {"AAA": [10.0, 12.0, 11.0, 14.0, 50.0, 13.0, 12.0, 15.0]},
        {"AAA": 100.0},
        n_quarters=8,
    )
    a = earnings_surprise_long(long)
    b = earnings_surprise_long(long)
    pd.testing.assert_frame_equal(a, b)


def test_empty_input_yields_empty_frame_with_schema() -> None:
    cols = ["ticker", "metric", "end", "filed", "value"]
    out = earnings_surprise_long(pd.DataFrame(columns=cols))
    assert list(out.columns) == [
        "ticker",
        "end",
        "filed",
        "eps_actual",
        "eps_expected",
        "surprise",
        "surprise_z",
    ]
    assert out.empty
    # as_of over an empty long -> all-NaN wide frame.
    wide = earnings_surprise_as_of(
        out,
        pd.DatetimeIndex(["2024-01-01", "2024-06-01"]).normalize(),
        ["AAA"],
    )
    assert wide.shape == (2, 1)
    assert wide["AAA"].isna().all()


def test_missing_column_raises() -> None:
    bad = pd.DataFrame([{"ticker": "AAA", "metric": "net_income", "end": "2024-03-31"}])
    with pytest.raises(ValueError, match="missing columns"):
        earnings_surprise_long(bad)
