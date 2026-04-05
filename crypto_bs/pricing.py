"""Black-76 coin-settled option pricing (undiscounted, r=0 in forward measure)."""

from __future__ import annotations

import numpy as np
from scipy.stats import norm

_MIN_T = 1.0 / 8760.0


def _validate_inputs(F: float, K: float, T: float, sigma: float) -> None:
    if F <= 0 or K <= 0:
        raise ValueError("Forward F and strike K must be positive")
    if T < 0:
        raise ValueError("Time to maturity T cannot be negative")
    if sigma <= 0:
        raise ValueError("Volatility sigma must be positive")


def _d1_d2(F: float, K: float, T: float, sigma: float) -> tuple[float, float]:
    _validate_inputs(F, K, T, sigma)
    T_eff = max(T, _MIN_T)
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T_eff) / (sigma * np.sqrt(T_eff))
    d2 = d1 - sigma * np.sqrt(T_eff)
    return d1, d2


def black_76_call(F: float, K: float, T: float, sigma: float) -> float:
    """Black-76 European call on forward, premium in coin (undiscounted)."""
    d1, d2 = _d1_d2(F, K, T, sigma)
    return float(norm.cdf(d1) - (K / F) * norm.cdf(d2))


def black_76_put(F: float, K: float, T: float, sigma: float) -> float:
    """Black-76 European put on forward, premium in coin (undiscounted)."""
    d1, d2 = _d1_d2(F, K, T, sigma)
    return float((K / F) * norm.cdf(-d2) - norm.cdf(-d1))


def price_option(F: float, K: float, T: float, sigma: float, option_type: str) -> float:
    """
    Price European options using Black-76 (coin-settled crypto style).

    F: forward price, K: strike, T: time in years, sigma: annualized vol.
    """
    if option_type.lower() == 'call':
        return black_76_call(F, K, T, sigma)
    if option_type.lower() == 'put':
        return black_76_put(F, K, T, sigma)
    raise ValueError("Invalid option_type: must be 'call' or 'put'")


def price_options_vectorized(
    F: float,
    K: np.ndarray,
    T: np.ndarray,
    sigma: np.ndarray,
    option_types: np.ndarray,
) -> np.ndarray:
    """
    Vectorized Black-76 coin premiums for a chain.

    option_types: array of 'call' / 'put' (or b'call' / b'put' for bytes).
    """
    K = np.asarray(K, dtype=float)
    T = np.asarray(T, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    if K.shape != T.shape or K.shape != sigma.shape or K.shape != option_types.shape:
        raise ValueError("K, T, sigma, and option_types must have the same shape")
    T_eff = np.maximum(T, _MIN_T)
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T_eff) / (sigma * np.sqrt(T_eff))
    d2 = d1 - sigma * np.sqrt(T_eff)
    calls = norm.cdf(d1) - (K / F) * norm.cdf(d2)
    puts = (K / F) * norm.cdf(-d2) - norm.cdf(-d1)
    ot = option_types
    if ot.dtype.kind in ('S', 'U'):
        is_call = np.char.lower(np.asarray(ot, dtype=str)) == 'call'
    else:
        is_call = np.asarray(ot) == 'call'
    return np.where(is_call, calls, puts)
