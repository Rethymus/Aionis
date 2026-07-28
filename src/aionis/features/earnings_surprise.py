"""Point-in-time earnings-surprise feature: actual EPS vs a naive seasonal
random-walk expectation (the same-quarter-prior-year EPS).

No free, PIT-safe CONSENSUS dataset exists (Bloomberg / Refinitiv / IBES are
proprietary and not point-in-time-vintage), so — following the same honesty as
:mod:`aionis.features.macro_surprise`'s statistical expectation — the
expectation here is the classic naive time-series benchmark from the
earnings-forecasting literature: ``EPS_q expected = EPS_{q-4}``, i.e. the firm's
own EPS for the same fiscal quarter one year earlier (the "seasonal random
walk"; Foster 1977, Lorek 1979, and the standard naive benchmark against which
analyst forecasts are evaluated). This is explicitly a TIME-SERIES expectation,
NOT a survey consensus — it carries no analyst information. The surprise is

    surprise   = (eps_actual - eps_expected) / |eps_expected|   (relative)
    surprise_z = per-ticker z-score of ``surprise`` over history-so-far (PIT)

PIT IS CRITICAL (same filing-date discipline as
:mod:`aionis.ingest.fundamentals`): an EPS surprise is KNOWABLE ONLY AT THE
FILING DATE of the report that contains it — NOT at its period-end ``end``. A
10-Q for Q1 (period-end Mar 31) filed May 2 is unknowable between Mar 31 and
May 2; using the period-end value in that gap is pure lookahead. Accordingly:

  * :func:`earnings_surprise_long` anchors every row to its ``filed`` date;
  * :func:`earnings_surprise_as_of` joins BACKWARD on ``filed`` (a surprise
    filed at F is visible at d >= F, NEVER at d < F) — mirroring
    :func:`aionis.ingest.fundamentals.pit_align`;
  * the q-4 expectation uses the prior-year-quarter EPS from a filing whose OWN
    filing date is <= the current filing date (the version knowable at filing,
    via ``merge_asof(direction="backward")`` on ``filed``);
  * the z-score mean/std are built ONLY from surprises filed STRICTLY BEFORE
    the current filing (``shift(1)`` before ``expanding`` — the PIT invariant,
    identical in spirit to :func:`aionis.features.macro_surprise.surprise_time_series`).

Permissive licenses only (pandas / numpy).
"""

from __future__ import annotations

import pandas as pd
import structlog

log = structlog.get_logger()

# Naive expectation = same fiscal quarter one year prior (seasonal random walk).
# End-month - 12 months is the match key: robust to fiscal-year relabeling and
# stub periods (a non-match -> NaN expected, the honest "can't compute" signal).
_PRIOR_QUARTER_OFFSET = pd.DateOffset(months=12)

# z-score is per-ticker, expanding over surprises FILED STRICTLY BEFORE the
# current filing. ddof=1 -> a finite std needs >= 2 strictly-prior valid
# surprises; min_periods=2 enforces that on the shift(1) prior series (pandas
# expanding counts non-NaN observations against min_periods).
Z_MIN_PERIODS = 2
Z_CLIP = 5.0  # |z| cap; matches macro_surprise.py fat-tail discipline

_OUT_COLUMNS = [
    "ticker",
    "end",
    "filed",
    "eps_actual",
    "eps_expected",
    "surprise",
    "surprise_z",
]


def earnings_surprise_long(
    fundamentals_long: pd.DataFrame,
    *,
    eps_num: str = "net_income",
    eps_den: str = "shares_out",
) -> pd.DataFrame:
    """Per (ticker, period) EPS actual, naive q-4 expected, and PIT surprise_z.

    EPS actual = ``eps_num`` / ``eps_den`` for the SAME filing (both pulled from
    ``fundamentals_long``, the long as-filed XBRL frame produced by
    :func:`aionis.ingest.fundamentals.build_fundamentals`: one row per fact with
    columns [ticker, metric, end, filed, form, fy, fp, value, unit]). NaN where
    the denominator is missing or <= 0 (negative/zero share count is not a
    meaningful EPS basis).

    Naive expected = EPS_{q-4}: the EPS of the same fiscal quarter one year
    earlier, matched by (ticker, period-end - 12 months). This is the seasonal
    random-walk / Foster-Lorek naive benchmark (NOT a survey consensus). NaN
    where no prior-year-quarter filing is knowable at the current filing date
    (the first four quarters of a firm's history carry no naive expectation).

    ``surprise``   = (actual - expected) / |expected|  — relative, sign-preserving
    via the absolute denominator. NaN where expected is NaN or zero.

    ``surprise_z`` = per-ticker z-score of ``surprise`` over its history-so-far:
    (surprise - expanding_mean) / expanding_std(ddof=1), where the expanding
    window runs over surprises FILED STRICTLY BEFORE the current filing
    (``shift(1)`` before ``expanding`` — the PIT invariant). NaN until >=
    ``Z_MIN_PERIODS`` strictly-prior surprises exist; clipped to +/- ``Z_CLIP``.

    Returns a long frame ``[ticker, end, filed, eps_actual, eps_expected,
    surprise, surprise_z]``. EVERY row is anchored to its FILING date
    (``filed``); the consumer aligns via :func:`earnings_surprise_as_of`.
    Period-end ``end`` is NEVER used as the knowable date (that would be
    lookahead). Only facts FILED <= the consumer's as-of date enter any join.
    """
    required = ["ticker", "metric", "end", "filed", "value"]
    if fundamentals_long is None or fundamentals_long.empty:
        log.warning("earnings_surprise_empty_input")
        return pd.DataFrame(columns=_OUT_COLUMNS)
    missing = [c for c in required if c not in fundamentals_long.columns]
    if missing:
        raise ValueError(f"fundamentals_long missing columns: {missing}")

    df = fundamentals_long[required].copy()
    df["end_dt"] = pd.to_datetime(df["end"])
    df["filed_dt"] = pd.to_datetime(df["filed"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["end_dt", "filed_dt"])

    def _one_metric(name: str) -> pd.DataFrame:
        sub = df[df["metric"] == name]
        if sub.empty:
            return pd.DataFrame(columns=["ticker", "end_dt", "filed_dt", name])
        # One value per filing (ticker, end, filed). Duplicate facts for the same
        # filing (e.g. a metric reported under two units) collapse to the last —
        # the same keep="last" discipline as pit_align's de-duplication.
        return (
            sub.sort_values("filed_dt")
            .drop_duplicates(["ticker", "end_dt", "filed_dt"], keep="last")[
                ["ticker", "end_dt", "filed_dt", "value"]
            ]
            .rename(columns={"value": name})
        )

    # Inner join: only filings reporting BOTH numerator and denominator carry an
    # EPS (a filing missing shares_out cannot yield an EPS — dropped, not imputed).
    per_filing = _one_metric(eps_num).merge(
        _one_metric(eps_den), on=["ticker", "end_dt", "filed_dt"], how="inner"
    )
    if per_filing.empty:
        log.warning(
            "earnings_surprise_no_filings_with_both_metrics",
            eps_num=eps_num,
            eps_den=eps_den,
        )
        return pd.DataFrame(columns=_OUT_COLUMNS)

    num = per_filing[eps_num]
    den = per_filing[eps_den]
    # NaN where denominator is missing or <= 0 (den > 0 is False for NaN too).
    per_filing["eps_actual"] = (num / den).where(den > 0)

    # --- naive q-4 expectation: prior-year-quarter EPS, PIT on filing date -------
    # For a current filing (ticker T, end E, filed F) the expectation is the EPS
    # of the filing with end == E - 12mo, whose OWN filing date is <= F (the
    # latest such = the version knowable at F). merge_asof backward on `filed`,
    # exact-matched by (ticker, prior_end) — identical mechanic to pit_align.
    per_filing = per_filing.sort_values("filed_dt").reset_index(drop=True)
    per_filing["prior_end"] = per_filing["end_dt"] - _PRIOR_QUARTER_OFFSET
    pool = (
        per_filing[["ticker", "end_dt", "filed_dt", "eps_actual"]]
        .rename(
            columns={
                "end_dt": "prior_end",
                "filed_dt": "prior_filed",
                "eps_actual": "eps_expected",
            }
        )
        .sort_values("prior_filed")
    )
    matched = pd.merge_asof(
        per_filing,
        pool,
        left_on="filed_dt",
        right_on="prior_filed",
        by=["ticker", "prior_end"],
        direction="backward",  # prior-year-quarter filing filed <= current filing (PIT)
    )

    expected = matched["eps_expected"]
    expected_abs = expected.abs()
    matched["surprise"] = ((matched["eps_actual"] - expected) / expected_abs).where(
        expected_abs > 0
    )  # NaN where expected is NaN (no q-4) or exactly 0

    # --- per-ticker z-score over history-so-far (strictly-past windows) ---------
    # Ordered by the filing-date timeline; shift(1) before expanding guarantees
    # the mean/std at filing F contain ONLY surprises filed strictly before F.
    matched = matched.sort_values(["ticker", "filed_dt", "end_dt"]).reset_index(drop=True)

    def _zscore(s: pd.Series) -> pd.Series:
        prior = s.shift(1)  # strictly-past surprises in filed-time
        mu = prior.expanding(min_periods=Z_MIN_PERIODS).mean()
        sigma = prior.expanding(min_periods=Z_MIN_PERIODS).std(ddof=1)
        return ((s - mu) / sigma).clip(-Z_CLIP, Z_CLIP)

    matched["surprise_z"] = matched.groupby("ticker", group_keys=False)["surprise"].transform(
        _zscore
    )

    out = (
        matched.assign(
            end=matched["end_dt"].dt.strftime("%Y-%m-%d"),
            filed=matched["filed_dt"].dt.strftime("%Y-%m-%d"),
        )[["ticker", "end", "filed", "eps_actual", "eps_expected", "surprise", "surprise_z"]]
        .sort_values(["ticker", "filed", "end"])
        .reset_index(drop=True)
    )
    log.info(
        "earnings_surprise_long_built",
        n_rows=len(out),
        n_tickers=out["ticker"].nunique(),
        n_with_expected=int(out["eps_expected"].notna().sum()),
        n_with_z=int(out["surprise_z"].notna().sum()),
    )
    return out


def earnings_surprise_as_of(
    surprise_long: pd.DataFrame,
    as_of_dates: pd.DatetimeIndex,
    tickers: list[str],
) -> pd.DataFrame:
    """PIT wide (as_of_dates x tickers) ``surprise_z``: at date d, the latest
    surprise whose FILING <= d.

    Backward ``merge_asof`` on ``filed`` (identical mechanic to
    :func:`aionis.ingest.fundamentals.pit_align`). NaN before a ticker's first
    filing, and before its first computable surprise_z. A surprise filed at F is
    visible at d >= F and NEVER at d < F — this is the PIT anchor: ``filed`` is
    the knowability date; period-end ``end`` is never used here.
    """
    dates = pd.DatetimeIndex(as_of_dates).normalize()
    wide = pd.DataFrame(index=dates, columns=list(tickers), dtype=float)
    if surprise_long is None or surprise_long.empty:
        return wide
    df = surprise_long.copy()
    df["filed_dt"] = pd.to_datetime(df["filed"])
    left = pd.DataFrame({"d": dates})
    for t in tickers:
        s = df[df["ticker"] == t].sort_values("filed_dt")
        if s.empty:
            continue
        # If two surprises share a filing date, the latest-row wins (keep="last"),
        # matching pit_align's tie handling.
        s = s.drop_duplicates("filed_dt", keep="last")[["filed_dt", "surprise_z"]]
        s = s.rename(columns={"filed_dt": "d"})
        m = pd.merge_asof(left, s, on="d", direction="backward")
        wide[t] = m["surprise_z"].to_numpy()
    return wide
