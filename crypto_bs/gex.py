"""Gamma exposure analytics for options chains."""

from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd
from scipy.stats import norm

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "strike",
    "time_to_maturity",
    "volatility",
    "option_type",
    "open_interest",
}

_MIN_T = 1.0 / 8760.0


def _validate_chain_df(chain_df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(chain_df.columns)
    if missing:
        raise ValueError(f"chain_df missing required columns: {sorted(missing)}")
    if chain_df.empty:
        raise ValueError("chain_df cannot be empty")


def compute_gex(
    chain_df: pd.DataFrame,
    spot: float,
    r: float = 0.0,
    contract_size: float = 1.0,
    dealer_convention: str = "short_gamma",
) -> pd.DataFrame:
    """
    Compute strike-level gamma exposure.

    Formula per line item:
    gex = sign * OI * gamma * spot^2 * contract_size
    where sign defaults to:
      - short_gamma: +1 for calls, -1 for puts
      - long_gamma:  -1 for calls, +1 for puts
    """
    _validate_chain_df(chain_df)
    if spot <= 0:
        raise ValueError("spot must be positive")
    if contract_size <= 0:
        raise ValueError("contract_size must be positive")
    if dealer_convention not in {"short_gamma", "long_gamma"}:
        raise ValueError("dealer_convention must be 'short_gamma' or 'long_gamma'")

    opt_types = chain_df["option_type"].astype(str).str.lower()
    if not opt_types.isin({"call", "put"}).all():
        raise ValueError("option_type must be call or put")

    n_rows = len(chain_df)
    row_spot = (
        chain_df["spot_price"].astype(float).to_numpy()
        if "spot_price" in chain_df.columns
        else np.full(n_rows, float(spot))
    )
    strikes = chain_df["strike"].astype(float).to_numpy()
    times = chain_df["time_to_maturity"].astype(float).to_numpy()
    vols = chain_df["volatility"].astype(float).to_numpy()
    open_interest = chain_df["open_interest"].astype(float).to_numpy()
    risk_free_rate = (
        chain_df["risk_free_rate"].astype(float).to_numpy()
        if "risk_free_rate" in chain_df.columns
        else np.full(n_rows, float(r))
    )
    dividend_yield = (
        chain_df["dividend_yield"].astype(float).to_numpy()
        if "dividend_yield" in chain_df.columns
        else np.zeros(n_rows, dtype=float)
    )
    is_coin_based = (
        chain_df["is_coin_based"].fillna(False).astype(bool).to_numpy()
        if "is_coin_based" in chain_df.columns
        else np.zeros(n_rows, dtype=bool)
    )

    if np.any(row_spot <= 0) or np.any(strikes <= 0):
        raise ValueError("spot_price and strike must be positive")
    if np.any(times < 0):
        raise ValueError("time_to_maturity cannot be negative")
    if np.any(vols <= 0):
        raise ValueError("volatility must be positive")

    t_eff = np.maximum(times, _MIN_T)
    sqrt_t = np.sqrt(t_eff)
    d1 = (
        np.log(row_spot / strikes)
        + (risk_free_rate - dividend_yield + 0.5 * vols**2) * t_eff
    ) / (vols * sqrt_t)

    gamma_usd = np.exp(-dividend_yield * t_eff) * norm.pdf(d1) / (row_spot * vols * sqrt_t)
    delta_usd = np.exp(-dividend_yield * t_eff) * norm.cdf(d1)
    gamma_coin = gamma_usd / row_spot - 2.0 * delta_usd / (row_spot**2)
    gamma_values = np.where(is_coin_based, gamma_coin, gamma_usd)

    call_sign = np.where(opt_types.to_numpy() == "call", 1.0, -1.0)
    signs = call_sign if dealer_convention == "short_gamma" else -call_sign
    gex_values = signs * open_interest * gamma_values * (spot**2) * contract_size

    details = pd.DataFrame(
        {
            "strike": strikes,
            "option_type": opt_types.values,
            "open_interest": open_interest,
            "gamma": gamma_values,
            "gex": gex_values,
        }
    )
    grouped = (
        details.groupby(["strike", "option_type"], as_index=False)["gex"]
        .sum()
        .pivot(index="strike", columns="option_type", values="gex")
        .fillna(0.0)
        .rename(columns={"call": "gex_call", "put": "gex_put"})
        .reset_index()
        .sort_values("strike")
    )
    if "gex_call" not in grouped.columns:
        grouped["gex_call"] = 0.0
    if "gex_put" not in grouped.columns:
        grouped["gex_put"] = 0.0
    grouped["gex_net"] = grouped["gex_call"] + grouped["gex_put"]
    grouped["cumulative_gex"] = grouped["gex_net"].cumsum()
    return grouped[["strike", "gex_call", "gex_put", "gex_net", "cumulative_gex"]]


def find_gamma_flip(gex_df: pd.DataFrame) -> Optional[float]:
    """Find strike where net GEX crosses zero (linear interpolation)."""
    if gex_df.empty:
        return None
    df = gex_df.sort_values("strike").reset_index(drop=True)
    net = df["gex_net"].values
    strikes = df["strike"].values
    if np.all(net >= 0) or np.all(net <= 0):
        return None
    for i in range(1, len(df)):
        y0, y1 = net[i - 1], net[i]
        if y0 == 0:
            return float(strikes[i - 1])
        if y0 * y1 < 0:
            x0, x1 = strikes[i - 1], strikes[i]
            return float(x0 + (0 - y0) * (x1 - x0) / (y1 - y0))
    return None


def gex_summary(gex_df: pd.DataFrame, spot: float) -> dict[str, float | str | bool | None]:
    """Return summary stats for a computed GEX dataframe."""
    if gex_df.empty:
        return {
            "total_gex": 0.0,
            "gamma_flip": None,
            "max_gex_strike": None,
            "regime": "neutral",
            "above_flip": None,
        }
    total = float(gex_df["gex_net"].sum())
    gamma_flip = find_gamma_flip(gex_df)
    max_idx = gex_df["gex_net"].abs().idxmax()
    max_strike = float(gex_df.loc[max_idx, "strike"])
    regime = "long_gamma" if total > 0 else "short_gamma" if total < 0 else "neutral"
    above_flip = None if gamma_flip is None else bool(spot >= gamma_flip)
    return {
        "total_gex": total,
        "gamma_flip": gamma_flip,
        "max_gex_strike": max_strike,
        "regime": regime,
        "above_flip": above_flip,
    }
