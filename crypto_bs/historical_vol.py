"""Historical volatility estimators for crypto options workflows."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _validate_series(name: str, values: pd.Series) -> None:
    if not isinstance(values, pd.Series):
        raise TypeError(f"{name} must be a pandas Series")
    if values.empty:
        raise ValueError(f"{name} cannot be empty")
    if (values <= 0).any():
        raise ValueError(f"{name} must contain strictly positive values")


def _validate_window(window: int) -> None:
    if window < 2:
        raise ValueError("window must be >= 2")


def close_to_close_hv(
    prices: pd.Series,
    window: int = 30,
    trading_days: int = 252,
) -> pd.Series:
    """Annualized close-to-close realized volatility."""
    _validate_series("prices", prices)
    _validate_window(window)
    log_returns = np.log(prices / prices.shift(1))
    return log_returns.rolling(window).std(ddof=0) * np.sqrt(trading_days)


def parkinson_hv(
    high: pd.Series,
    low: pd.Series,
    window: int = 30,
    trading_days: int = 252,
) -> pd.Series:
    """Annualized Parkinson volatility estimator using high/low range."""
    _validate_series("high", high)
    _validate_series("low", low)
    _validate_window(window)
    if len(high) != len(low):
        raise ValueError("high and low must have the same length")
    if (high < low).any():
        raise ValueError("high must be >= low for all observations")

    hl_sq = np.log(high / low) ** 2
    var = hl_sq.rolling(window).mean() / (4 * np.log(2))
    return np.sqrt(var * trading_days)


def rogers_satchell_hv(
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 30,
    trading_days: int = 252,
) -> pd.Series:
    """Annualized Rogers-Satchell volatility estimator."""
    _validate_series("open_", open_)
    _validate_series("high", high)
    _validate_series("low", low)
    _validate_series("close", close)
    _validate_window(window)
    if not (len(open_) == len(high) == len(low) == len(close)):
        raise ValueError("open_, high, low, close must have the same length")
    if (high < low).any():
        raise ValueError("high must be >= low for all observations")

    log_ho = np.log(high / open_)
    log_lo = np.log(low / open_)
    log_co = np.log(close / open_)
    rs_term = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)
    var = rs_term.rolling(window).mean()
    return np.sqrt(var * trading_days)


def yang_zhang_hv(
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 30,
    trading_days: int = 252,
) -> pd.Series:
    """Annualized Yang-Zhang volatility estimator."""
    _validate_series("open_", open_)
    _validate_series("high", high)
    _validate_series("low", low)
    _validate_series("close", close)
    _validate_window(window)
    if not (len(open_) == len(high) == len(low) == len(close)):
        raise ValueError("open_, high, low, close must have the same length")
    if (high < low).any():
        raise ValueError("high must be >= low for all observations")

    log_oc = np.log(close / open_)
    log_oo = np.log(open_ / close.shift(1))

    log_ho = np.log(high / open_)
    log_lo = np.log(low / open_)
    rs_term = log_ho * (log_ho - log_oc) + log_lo * (log_lo - log_oc)

    sigma_o2 = log_oo.rolling(window).var(ddof=0)
    sigma_c2 = log_oc.rolling(window).var(ddof=0)
    sigma_rs = rs_term.rolling(window).mean()

    k = 0.34 / (1.34 + (window + 1) / (window - 1))
    yz_var = sigma_o2 + k * sigma_c2 + (1 - k) * sigma_rs
    return np.sqrt(yz_var * trading_days)


def vol_premium(implied_vol: pd.Series, realized_vol: pd.Series) -> pd.Series:
    """Return implied-minus-realized volatility spread."""
    _validate_series("implied_vol", implied_vol)
    _validate_series("realized_vol", realized_vol)
    if len(implied_vol) != len(realized_vol):
        raise ValueError("implied_vol and realized_vol must have the same length")
    return implied_vol - realized_vol
