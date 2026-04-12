"""Volatility analytics and simple regime signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Dict, Optional

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from .surface import VolatilitySurface


@dataclass
class VolatilityAnalytics:
    """
    Analytics over ATM term structure, skew, and historical context.

    Inputs are intentionally simple Series objects so this can be used before
    a full surface object is available.
    """

    atm_term_structure: pd.Series  # index: maturity in years, value: ATM IV
    skew_by_maturity: Optional[pd.Series] = None  # value: 25d put - 25d call IV
    historical_atm_iv: Optional[pd.Series] = None  # time series for IV percentile

    def __post_init__(self) -> None:
        if self.atm_term_structure.empty:
            raise ValueError("atm_term_structure cannot be empty")
        if (self.atm_term_structure <= 0).any():
            raise ValueError("atm_term_structure must be positive")

    @classmethod
    def from_surface(
        cls,
        surface: "VolatilitySurface",
        *,
        maturities: Optional[list[float]] = None,
        historical_atm_iv: Optional[pd.Series] = None,
        delta: float = 0.25,
    ) -> "VolatilityAnalytics":
        """
        Construct analytics inputs directly from a fitted `VolatilitySurface`.

        The resulting `skew_by_maturity` uses `surface.get_skew(...)`, which is
        delta-aware when the surface was fit with `underlying_price` and
        `option_type` columns.
        """
        term = surface.get_term_structure()
        chosen_maturities = (
            list(term.index.astype(float))
            if maturities is None
            else [float(maturity) for maturity in maturities]
        )
        skew = pd.Series(
            {maturity: surface.get_skew(maturity, delta=delta) for maturity in chosen_maturities},
            dtype=float,
        ).sort_index()
        return cls(
            atm_term_structure=term,
            skew_by_maturity=skew,
            historical_atm_iv=historical_atm_iv,
        )

    def _nearest_iv(self, target_t: float) -> float:
        idx = np.asarray(self.atm_term_structure.index, dtype=float)
        vals = np.asarray(self.atm_term_structure.values, dtype=float)
        nearest = int(np.abs(idx - target_t).argmin())
        return float(vals[nearest])

    def iv_percentile(self, lookback_days: int = 252) -> float:
        """Percentile rank of latest ATM IV in recent historical ATM series."""
        if self.historical_atm_iv is None or self.historical_atm_iv.empty:
            raise ValueError("historical_atm_iv is required for iv_percentile()")
        hist = self.historical_atm_iv.dropna().tail(lookback_days)
        if hist.empty:
            raise ValueError("historical_atm_iv has no usable values")
        current = float(hist.iloc[-1])
        percentile = float((hist <= current).mean() * 100.0)
        return percentile

    def vol_premium(self, hv_30d: float) -> float:
        """ATM(30d) implied vol minus supplied realized vol."""
        if hv_30d <= 0:
            raise ValueError("hv_30d must be positive")
        iv_30d = self._nearest_iv(30.0 / 365.0)
        return float(iv_30d - hv_30d)

    def skew_regime(self) -> str:
        """Classify skew regime from nearest 30d skew."""
        if self.skew_by_maturity is None or self.skew_by_maturity.empty:
            return "UNKNOWN"
        idx = np.asarray(self.skew_by_maturity.index, dtype=float)
        vals = np.asarray(self.skew_by_maturity.values, dtype=float)
        nearest = int(np.abs(idx - (30.0 / 365.0)).argmin())
        skew = float(vals[nearest])
        if skew > 0.03:
            return "STEEP"
        if skew < -0.01:
            return "INVERTED"
        return "NORMAL"

    def ts_regime(self) -> str:
        """Term-structure regime using 7d/30d ATM ratio."""
        iv_7d = self._nearest_iv(7.0 / 365.0)
        iv_30d = self._nearest_iv(30.0 / 365.0)
        ratio = iv_7d / iv_30d
        if ratio > 1.05:
            return "BACKWARDATION"
        if ratio < 0.95:
            return "CONTANGO"
        return "FLAT"

    def trading_signal(self) -> Dict[str, float | str]:
        """
        Synthesize regime metrics into coarse directional signals.

        Positive signal means "buy vol bias"; negative means "sell vol bias".
        """
        ts = self.ts_regime()
        skew = self.skew_regime()
        ts_signal = 1.0 if ts == "BACKWARDATION" else -1.0 if ts == "CONTANGO" else 0.0
        skew_signal = -0.5 if skew == "STEEP" else 0.5 if skew == "INVERTED" else 0.0
        total = ts_signal + skew_signal
        return {
            "ts_regime": ts,
            "skew_regime": skew,
            "ts_signal": ts_signal,
            "skew_signal": skew_signal,
            "total_signal": total,
        }
