"""Fama-French 5-factor residual regression (statsmodels OLS + pandas-datareader).

将选股策略收益分解为 α + β_MKT + β_SMB + β_HML + β_RMW + β_CMA。
使用 statsmodels.OLS + cov_type='HAC' (Newey-West) 获取稳健标准误。

探索性 track_b 工具（未接入 pipeline，不写 ledger），纯 OSS 复用。
"""
from __future__ import annotations

from typing import TypedDict

import numpy as np
import pandas as pd
import structlog

log = structlog.get_logger()

# Newey-West rule-of-thumb constant (Newey & West, 1994)
_NEWEY_WEST_LAG_FACTOR = 4

# Minimum observations for meaningful regression
_MIN_OBS = 12

# Column names expected in FF5 data from Kenneth-French database
_FF5_FACTOR_COLUMNS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]
_RF_COLUMN = "RF"


class FF5Regression(TypedDict):
    """FF5 regression output."""
    alpha: float  # monthly alpha (intercept)
    alpha_t: float  # HAC t-stat for alpha
    alpha_p: float  # two-sided p-value for alpha
    beta_mkt: float  # market beta
    beta_smb: float  # size (SMB) beta
    beta_hml: float  # value (HML) beta
    beta_rmw: float  # profitability (RMW) beta
    beta_cma: float  # investment (CMA) beta
    r_squared: float  # R-squared of regression
    n_obs: int  # number of observations
    maxlag: int  # Newey-West lags used


def _validate_ff5_columns(ff5_data: pd.DataFrame) -> None:
    """Validate that FF5 data has all required columns.

    Raises:
        ValueError: If required columns are missing.
    """
    required = _FF5_FACTOR_COLUMNS + [_RF_COLUMN]
    missing = [col for col in required if col not in ff5_data.columns]
    if missing:
        raise ValueError(f"FF5 data missing required columns: {missing}")


def _newey_west_maxlag(n_obs: int) -> int:
    """Compute Newey-West lag using rule-of-thumb: 4*(n/100)^(2/9).

    Args:
        n_obs: Number of observations.

    Returns:
        Recommended maxlag (at least 1).
    """
    if n_obs < 2:
        return 1
    return max(1, int(_NEWEY_WEST_LAG_FACTOR * (n_obs / 100.0) ** (2 / 9)))


def _make_nan_regression() -> FF5Regression:
    """Return a FF5Regression with all NaN values (insufficient data)."""
    return FF5Regression(
        alpha=float("nan"),
        alpha_t=float("nan"),
        alpha_p=float("nan"),
        beta_mkt=float("nan"),
        beta_smb=float("nan"),
        beta_hml=float("nan"),
        beta_rmw=float("nan"),
        beta_cma=float("nan"),
        r_squared=float("nan"),
        n_obs=0,
        maxlag=0,
    )


def ff5_residual_regression(
    strategy_returns: pd.Series,
    ff5_data: pd.DataFrame,
    maxlag: int | None = None,
) -> FF5Regression:
    """Run FF5 residual regression with Newey-West HAC standard errors.

    Decomposes strategy returns into α (abnormal return) and factor loadings
    (β) for the five Fama-French factors. Uses HAC (heteroskedasticity and
    autocorrelation consistent) covariance estimation for robust inference.

    Args:
        strategy_returns: Monthly long/short strategy returns, date-indexed.
        ff5_data: FF5 factor data from pandas-datareader or equivalent.
                   Expected columns: Mkt-RF, SMB, HML, RMW, CMA, RF (plus a 'date'
                   column or DatetimeIndex). All values in decimal (e.g., 0.01 for 1%).
        maxlag: Newey-West lag parameter. If None, uses rule-of-thumb:
                4 * (n/100)^(2/9) per Newey & West (1994).

    Returns:
        FF5Regression dict with alpha, betas, t-stats, p-values, R², n_obs,
        and the maxlag used. Returns NaN values if insufficient data (<12 obs).

    Raises:
        ValueError: If ff5_data lacks required columns.

    Note on leakage:
        FF5 factors from Kenneth-French database lack vintage information
        (historical revisions are not published). This introduces potential
        minor lookahead bias. For exploratory track_b use only; not for
        final production claims without vintage correction.
    """
    import statsmodels.api as sm
    from statsmodels.regression.linear_model import OLS

    # Validate input columns
    _validate_ff5_columns(ff5_data)

    # Prepare FF5 data: ensure date index
    df = ff5_data.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()
        df = df.set_index("date")
    else:
        df.index = pd.to_datetime(df.index).normalize()

    # Prepare strategy returns: normalize index
    strat = strategy_returns.copy()
    strat.index = pd.to_datetime(strat.index).normalize()

    # Inner join on date (only common periods)
    merged = df.join(strat.to_frame("strategy"), how="inner")

    if len(merged) < _MIN_OBS:
        log.warning(
            "ff5_insufficient_obs",
            n_obs=len(merged),
            min_obs=_MIN_OBS,
        )
        result = _make_nan_regression()
        result["n_obs"] = len(merged)
        return result

    # Excess returns = strategy - RF
    y = merged["strategy"].to_numpy(dtype=float) - merged[_RF_COLUMN].to_numpy(
        dtype=float
    )

    # FF5 factors (excess market is already Mkt-RF)
    X = merged[_FF5_FACTOR_COLUMNS].to_numpy(dtype=float)
    X = sm.add_constant(X)  # adds intercept column (alpha)

    # Compute Newey-West lags if not provided
    n = len(y)
    nw_lag = maxlag if maxlag is not None else _newey_west_maxlag(n)

    # OLS with HAC covariance (Newey-West)
    try:
        model = OLS(y, X)
        res = model.fit(cov_type="HAC", cov_kwds={"maxlags": nw_lag})
    except Exception as e:
        log.error("ff5_regression_failed", error=str(e))
        result = _make_nan_regression()
        result["n_obs"] = n
        return result

    # Extract coefficients and statistics
    params = res.params
    t_stats = res.tvalues
    p_values = res.pvalues

    return FF5Regression(
        alpha=float(params[0]),
        alpha_t=float(t_stats[0]),
        alpha_p=float(p_values[0]),
        beta_mkt=float(params[1]),
        beta_smb=float(params[2]),
        beta_hml=float(params[3]),
        beta_rmw=float(params[4]),
        beta_cma=float(params[5]),
        r_squared=float(res.rsquared),
        n_obs=n,
        maxlag=nw_lag,
    )


def amihud_illiquidity(
    prices: pd.DataFrame,
    volume: pd.DataFrame,
    window: int = 21,
) -> pd.DataFrame:
    """Compute Amihud (2002) illiquidity ratio: |ret| / dollar_volume.

    The illiquidity measure captures the price impact of trading. Higher values
    indicate less liquid stocks (larger price movement per dollar traded).

    Formula (Amihud, 2002, JFM):
        Illiq_i,t = (1/D_t) * Σ_d |r_i,d| / (Volume_i,d * Price_i,d)

    where:
        - D_t is the number of trading days in the window
        - r_i,d is the daily return for stock i on day d
        - Volume_i,d is the trading volume
        - Price_i,d is the closing price

    Args:
        prices: DataFrame with columns [date, ticker, close] (or equivalent).
        volume: DataFrame with columns [date, ticker, volume].
        window: Rolling window in trading days (default 21 ≈ 1 month).

    Returns:
        DataFrame with columns [date, ticker, illiq], where illiq is the
        rolling average illiquidity ratio. Rows with insufficient data are
        dropped.

    Raises:
        ValueError: If input DataFrames lack required columns.

    Note:
        First observation per ticker has NaN return (no previous price),
        so illiq is NaN for that row and dropped.
    """
    _PRICES_REQUIRED = {"date", "ticker", "close"}
    _VOLUME_REQUIRED = {"date", "ticker", "volume"}

    if not _PRICES_REQUIRED.issubset(prices.columns):
        raise ValueError(f"prices missing columns: {_PRICES_REQUIRED - set(prices.columns)}")
    if not _VOLUME_REQUIRED.issubset(volume.columns):
        raise ValueError(f"volume missing columns: {_VOLUME_REQUIRED.issubset(volume.columns)}")

    # Merge price and volume on date/ticker
    df = prices.merge(volume, on=["date", "ticker"], how="inner", suffixes=("", "_vol"))

    # Sort by ticker then date for correct pct_change
    df = df.sort_values(["ticker", "date"]).copy()

    # Compute daily returns
    df["ret"] = df.groupby("ticker")["close"].pct_change()

    # Dollar volume = price * volume
    df["dollar_vol"] = df["close"] * df["volume"]

    # Absolute return / dollar volume (handle div by zero)
    df["illiq_daily"] = df["ret"].abs() / df["dollar_vol"].replace(0, np.nan)

    # Rolling mean over window (per ticker)
    df["illiq"] = df.groupby("ticker")["illiq_daily"].transform(
        lambda x: x.rolling(window, min_periods=1).mean()
    )

    # Drop rows where illiq is NaN (first row per ticker + div/zero cases)
    result = df[["date", "ticker", "illiq"]].dropna()

    return result


def _fallback_load_ff5(start: str, end: str) -> pd.DataFrame | None:
    """Fallback: Download FF5 from Kenneth-French bulk ZIP directly.

    Uses the official 2x3 CSV ZIP file as fallback when pandas-datareader fails.
    This is a POST-2014 update to the FF5 factor construction.

    Args:
        start: Start date (YYYY-MM-DD).
        end: End date (YYYY-MM-DD).

    Returns:
        DataFrame with columns: date, Mkt-RF, SMB, HML, RMW, CMA, RF.
        Returns None if download fails.
    """
    import io
    import zipfile

    from aionis.ingest.universe import _policy_get

    # Official Kenneth-French bulk ZIP (2x3 construction, post-2014)
    zip_url = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip"

    log.info("ff5_fallback_attempt", url=zip_url)

    try:
        # Shared >=2s host-spacing policy (round 56: replaced the off-policy
        # bare urlopen flagged by audit; one bounded retry is kept).
        resp = _policy_get(zip_url, timeout=30)
        resp.raise_for_status()
        raw_zip = resp.content
    except Exception as e:
        log.error("ff5_fallback_failed", error=str(e))
        return None

    # Read CSV from ZIP in memory
    try:
        with zipfile.ZipFile(io.BytesIO(raw_zip)) as zf:
            # The CSV file is named 'F-F_Research_Data_5_Factors_2x3.csv'
            csv_name = "F-F_Research_Data_5_Factors_2x3.csv"
            with zf.open(csv_name) as f:
                # Format: 3 doc lines, 1 blank line, header line, then monthly data
                # Skip first 4 rows (3 doc + 1 blank)
                # Read monthly data only (755 rows from 196307 to 202605)
                df = pd.read_csv(f, skiprows=4, encoding="latin1", nrows=755)
    except Exception as e:
        log.error("ff5_zip_parse_failed", error=str(e))
        return None

    # Parse period column (YYYYMM format like "196307")
    period_col = df.columns[0]  # First unnamed column is the period
    df = df.rename(columns={period_col: "period"})

    # Convert period (YYYYMM) to datetime (month-end)
    df["date"] = pd.to_datetime(df["period"].astype(str), format="%Y%m") + pd.offsets.MonthEnd(0)
    df = df.drop(columns=["period"])

    # Convert from percentage to decimal
    for col in ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]:
        if col in df.columns:
            df[col] = df[col] / 100.0

    # Ensure column order and filter by date range
    expected_cols = ["date", "Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]
    df = df[expected_cols]

    start_dt = pd.to_datetime(start).normalize()
    end_dt = pd.to_datetime(end).normalize()
    df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]

    log.info("ff5_fallback_success", n_rows=len(df))
    return df


def load_ff5(start: str, end: str) -> pd.DataFrame:
    """Load Fama-French 5-factor data from Kenneth-French database.

    This is a convenience wrapper around pandas_datareader for fetching
    FF5 factor returns, with fallback to direct bulk ZIP download.
    DO NOT call this in tests (network dependency).

    Args:
        start: Start date (YYYY-MM-DD).
        end: End date (YYYY-MM-DD).

    Returns:
        DataFrame with columns: date, Mkt-RF, SMB, HML, RMW, CMA, RF.
        Values are in decimal form (e.g., 0.01 for 1%).

    Raises:
        Exception: If fetch fails (network, API change, etc.).

    Note:
        FF5 data lacks vintage information. The returned series reflects
        the current database values, not historical point-in-time values.
        Use for exploratory analysis only.
    """
    import pandas_datareader.data as web

    try:
        # Fetch FF5 research data (monthly frequency)
        # dataset name: "Fama_French_5_Factors"
        df = web.DataReader("Fama_French_5_Factors", "famafrench", start=start, end=end)[0]

        # Reset index to make date a column
        df = df.reset_index()

        # Rename columns to match expected names (pandas_datareader uses "Mkt-RF" etc.)
        # The data comes with "Date" as period; convert to datetime
        df.columns = [col.replace("Mkt-RF", "Mkt-RF") for col in df.columns]

        # Convert Period to datetime
        df["date"] = df["Date"].dt.to_timestamp()
        df = df.drop(columns=["Date"])

        # Ensure column order
        expected_cols = ["date", "Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]
        df = df[expected_cols]

        # Convert from percentage basis points to decimal
        for col in ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]:
            df[col] = df[col] / 100.0

        return df
    except Exception as e:
        log.warning("ff5_pdr_failed", error=str(e))
        # Fallback to direct bulk ZIP download
        df = _fallback_load_ff5(start, end)
        if df is None:
            raise
        return df
