"""Gamma exposure analytics for options chains."""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

from .black_scholes import BlackScholesModel, OptionParameters, OptionType


REQUIRED_COLUMNS = {
    "strike",
    "time_to_maturity",
    "volatility",
    "option_type",
    "open_interest",
}


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

    bs = BlackScholesModel()
    rows = []
    for _, row in chain_df.iterrows():
        opt = str(row["option_type"]).lower()
        if opt not in {"call", "put"}:
            raise ValueError("option_type must be call or put")
        params = OptionParameters(
            spot_price=float(row.get("spot_price", spot)),
            strike_price=float(row["strike"]),
            time_to_maturity=float(row["time_to_maturity"]),
            volatility=float(row["volatility"]),
            risk_free_rate=float(row.get("risk_free_rate", r)),
            option_type=OptionType.CALL if opt == "call" else OptionType.PUT,
            is_coin_based=bool(row.get("is_coin_based", False)),
        )
        gamma = bs.calculate_option_price(params).gamma
        oi = float(row["open_interest"])

        if dealer_convention == "short_gamma":
            sign = 1.0 if opt == "call" else -1.0
        else:
            sign = -1.0 if opt == "call" else 1.0

        gex = sign * oi * gamma * (spot**2) * contract_size
        rows.append(
            {
                "strike": float(row["strike"]),
                "option_type": opt,
                "open_interest": oi,
                "gamma": gamma,
                "gex": gex,
            }
        )

    details = pd.DataFrame(rows)
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


def gex_summary(gex_df: pd.DataFrame, spot: float) -> Dict[str, Optional[float]]:
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
