"""Black-76 Greeks on forward F (coin-settled options, r=0 in d1/d2)."""

from __future__ import annotations

import numpy as np
from scipy.stats import norm

_MIN_T = 1.0 / 8760.0  # one hour in years


def _validate_inputs(F: float, K: float, T: float, sigma: float) -> None:
    if F <= 0 or K <= 0:
        raise ValueError("Forward F and strike K must be positive")
    if T < 0:
        raise ValueError("Time to maturity T cannot be negative")
    if sigma <= 0:
        raise ValueError("Volatility sigma must be positive")


def calculate_d1(F: float, K: float, T: float, sigma: float) -> float:
    _validate_inputs(F, K, T, sigma)
    T_eff = max(T, _MIN_T)
    return (np.log(F / K) + 0.5 * sigma**2 * T_eff) / (sigma * np.sqrt(T_eff))


def calculate_d2(F: float, K: float, T: float, sigma: float) -> float:
    _validate_inputs(F, K, T, sigma)
    T_eff = max(T, _MIN_T)
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T_eff) / (sigma * np.sqrt(T_eff))
    return d1 - sigma * np.sqrt(T_eff)


def delta(F: float, K: float, T: float, sigma: float, option_type: str) -> float:
    d1 = calculate_d1(F, K, T, sigma)
    if option_type.lower() == 'call':
        return float(norm.cdf(d1))
    if option_type.lower() == 'put':
        return float(norm.cdf(d1) - 1)
    raise ValueError("Invalid option_type: must be 'call' or 'put'")


def gamma(F: float, K: float, T: float, sigma: float) -> float:
    d1 = calculate_d1(F, K, T, sigma)
    T_eff = max(T, _MIN_T)
    return float(norm.pdf(d1) / (F * sigma * np.sqrt(T_eff)))


def vega(F: float, K: float, T: float, sigma: float) -> float:
    d1 = calculate_d1(F, K, T, sigma)
    T_eff = max(T, _MIN_T)
    return float(F * np.sqrt(T_eff) * norm.pdf(d1))


def theta(F: float, K: float, T: float, sigma: float, option_type: str) -> float:
    d1 = calculate_d1(F, K, T, sigma)
    T_eff = max(T, _MIN_T)
    if option_type.lower() == 'call':
        return float(-(F * sigma * norm.pdf(d1)) / (2 * np.sqrt(T_eff)))
    if option_type.lower() == 'put':
        return float(-(F * sigma * norm.pdf(d1)) / (2 * np.sqrt(T_eff)))
    raise ValueError("Invalid option_type: must be 'call' or 'put'")


def rho(
    F: float,
    K: float,
    T: float,
    sigma: float,
    option_type: str,
    risk_free_rate: float = 0.0,
) -> float:
    """
    Sensitivity of discounted coin premium to r, per 1% rate move: -T exp(-rT) V / 100.

    V is the undiscounted Black-76 coin price (same as ``price_option``). d1, d2 match
    that model. When ``risk_free_rate`` is 0, rho = -T * V / 100.
    """
    _validate_inputs(F, K, T, sigma)
    T_eff = max(T, _MIN_T)
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T_eff) / (sigma * np.sqrt(T_eff))
    d2 = d1 - sigma * np.sqrt(T_eff)
    # Undiscounted premium in coin (same units as price_option / Black-76 here)
    if option_type.lower() == 'call':
        undisc = norm.cdf(d1) - (K / F) * norm.cdf(d2)
    elif option_type.lower() == 'put':
        undisc = (K / F) * norm.cdf(-d2) - norm.cdf(-d1)
    else:
        raise ValueError("Invalid option_type: must be 'call' or 'put'")
    discounted = np.exp(-risk_free_rate * T_eff) * undisc
    return float(-T_eff * discounted / 100.0)
