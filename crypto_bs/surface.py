"""Simple implied volatility surface utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class VolatilitySurface:
    """
    Lightweight IV surface for strike/time interpolation.

    Expected fit columns:
    - strike
    - time_to_maturity (years)
    - implied_volatility
    """

    _by_t: Dict[float, pd.DataFrame] = field(default_factory=dict)
    _term: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))

    def fit(self, chain_df: pd.DataFrame) -> None:
        required = {"strike", "time_to_maturity", "implied_volatility"}
        missing = required.difference(chain_df.columns)
        if missing:
            raise ValueError(f"chain_df missing required columns: {sorted(missing)}")
        if chain_df.empty:
            raise ValueError("chain_df cannot be empty")

        clean = chain_df[list(required)].copy()
        clean = clean.dropna()
        if (clean["implied_volatility"] <= 0).any():
            raise ValueError("implied_volatility must be positive")

        self._by_t = {}
        term = {}
        for t, grp in clean.groupby("time_to_maturity"):
            g = grp.sort_values("strike").reset_index(drop=True)
            self._by_t[float(t)] = g
            # ATM proxy: strike nearest median strike
            k_med = float(g["strike"].median())
            atm_idx = (g["strike"] - k_med).abs().idxmin()
            term[float(t)] = float(g.loc[atm_idx, "implied_volatility"])
        self._term = pd.Series(term).sort_index()

    def _interp_strike(self, t: float, strike: float) -> float:
        if t not in self._by_t:
            raise KeyError(f"time_to_maturity {t} not fitted")
        g = self._by_t[t]
        x = g["strike"].to_numpy(dtype=float)
        y = g["implied_volatility"].to_numpy(dtype=float)
        return float(np.interp(strike, x, y))

    def get_iv(self, strike: float, time_to_maturity: float) -> float:
        """Interpolate IV across strike, then linearly across maturities."""
        if not self._by_t:
            raise ValueError("surface not fitted")
        t_values = np.array(sorted(self._by_t.keys()), dtype=float)
        if len(t_values) == 1:
            return self._interp_strike(float(t_values[0]), strike)
        iv_at_t = np.array([self._interp_strike(float(t), strike) for t in t_values], dtype=float)
        return float(np.interp(time_to_maturity, t_values, iv_at_t))

    def get_atm_iv(self, time_to_maturity: float) -> float:
        """Return ATM IV from fitted term structure with linear interpolation."""
        if self._term.empty:
            raise ValueError("surface not fitted")
        x = self._term.index.to_numpy(dtype=float)
        y = self._term.values.astype(float)
        return float(np.interp(time_to_maturity, x, y))

    def get_term_structure(self) -> pd.Series:
        if self._term.empty:
            raise ValueError("surface not fitted")
        return self._term.copy()

    def get_skew(self, time_to_maturity: float, delta: float = 0.25) -> float:
        """
        Approximate skew as IV(low strike) - IV(high strike) around ATM.
        Uses a strike percentile proxy based on `delta`.
        """
        if not self._by_t:
            raise ValueError("surface not fitted")
        nearest_t = min(self._by_t.keys(), key=lambda tt: abs(tt - time_to_maturity))
        g = self._by_t[nearest_t]
        strikes = g["strike"].to_numpy(dtype=float)
        q_low = np.quantile(strikes, max(0.0, delta))
        q_high = np.quantile(strikes, min(1.0, 1 - delta))
        iv_low = self._interp_strike(float(nearest_t), float(q_low))
        iv_high = self._interp_strike(float(nearest_t), float(q_high))
        return float(iv_low - iv_high)

    def check_arbitrage(self) -> Dict[str, List[str]]:
        """
        Basic consistency checks (not full no-arbitrage proof).
        - Butterfly proxy: IV should be reasonably smooth by strike.
        - Calendar proxy: ATM IV shouldn't jump excessively between adjacent maturities.
        """
        issues = {"butterfly": [], "calendar": []}
        if not self._by_t:
            return issues
        for t, g in self._by_t.items():
            iv = g["implied_volatility"].to_numpy(dtype=float)
            if len(iv) >= 3:
                second_diff = np.diff(iv, n=2)
                if np.any(np.abs(second_diff) > 0.35):
                    issues["butterfly"].append(f"irregular smile curvature at T={t:.6f}")
        if len(self._term) >= 2:
            ts = self._term.sort_index()
            jumps = np.abs(np.diff(ts.values.astype(float)))
            for i, j in enumerate(jumps):
                if j > 0.25:
                    t0 = ts.index[i]
                    t1 = ts.index[i + 1]
                    issues["calendar"].append(f"large ATM-IV jump between T={t0:.6f} and T={t1:.6f}")
        return issues
