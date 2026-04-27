"""Utility functions and configuration defaults for crypto options analytics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CryptoVolConfig:
    """Central configuration dataclass with crypto-appropriate defaults.

    Use this object to keep application-level defaults consistent across
    pricing, surface, and risk workflows.

    Attributes:
        trading_days: Calendar days per year for annualizing realized volatility.
            Crypto trades 24/7/365; equities use 252.
        vol_of_vol: Volatility-of-volatility for Monte Carlo VaR/CVaR simulations.
            BTC VoV is 0.80–2.00+ in normal conditions; TradFi equity default is 0.25.
            Use 1.5–2.0 for stress scenarios.
        spot_vol_correlation: Correlation between spot returns and vol shocks.
            Negative for most assets (vol rises as spot falls).
        default_risk_free_rate: Risk-free rate for discounting.
            Crypto coin-settled options use r=0 in the forward measure.
        min_time_to_maturity: Minimum T (years) used as floor to avoid division by zero.
            Defaults to 1 hour.
    """

    trading_days: int = 365
    vol_of_vol: float = 0.80
    spot_vol_correlation: float = -0.20
    default_risk_free_rate: float = 0.0
    min_time_to_maturity: float = 1.0 / 8760.0  # 1 hour in years


def breakeven_price(K: float, premium: float, option_type: str) -> float:
    """
    Calculate the breakeven underlying price at expiration for USD-denominated premium.

    This simple formula assumes the premium is in the same units as the strike (USD).
    """
    if option_type.lower() == 'call':
        return K + premium
    elif option_type.lower() == 'put':
        return K - premium
    else:
        raise ValueError("Invalid option_type: must be 'call' or 'put'")


def breakeven_price_coin_based(K: float, premium_coin: float, option_type: str) -> float:
    """
    Breakeven underlying price for coin-settled options (premium in coin units).

    For coin-based options (e.g., BTC-settled):
    - Call: payoff in coin is max(S - K, 0)/S. Breakeven when (S - K)/S = premium_coin -> S = K / (1 - premium_coin)
    - Put:  payoff in coin is max(K - S, 0)/S. Breakeven when (K - S)/S = premium_coin -> S = K / (1 + premium_coin)

    Args:
        K: Strike price (USD)
        premium_coin: Premium paid in underlying coin units (e.g., BTC)
        option_type: 'call' or 'put'

    Returns:
        Breakeven underlying price S* in USD
    """
    ot = option_type.lower()
    if ot not in ("call", "put"):
        raise ValueError("Invalid option_type: must be 'call' or 'put'")

    if premium_coin < 0:
        raise ValueError("premium_coin must be non-negative")

    if ot == 'call':
        if premium_coin >= 1:
            raise ValueError("For calls, premium_coin must be < 1 for a finite breakeven")
        return K / (1 - premium_coin)
    else:  # put
        return K / (1 + premium_coin)
