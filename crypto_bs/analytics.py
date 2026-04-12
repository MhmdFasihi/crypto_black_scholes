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

    def _nearest_skew(self, target_t: float) -> float:
        if self.skew_by_maturity is None or self.skew_by_maturity.empty:
            raise ValueError("skew_by_maturity is required for skew_term_metrics()")
        idx = np.asarray(self.skew_by_maturity.index, dtype=float)
        vals = np.asarray(self.skew_by_maturity.values, dtype=float)
        nearest = int(np.abs(idx - target_t).argmin())
        return float(vals[nearest])

    def term_structure_metrics(
        self,
        front_target: float = 7.0 / 365.0,
        anchor_target: float = 30.0 / 365.0,
        back_target: float = 90.0 / 365.0,
    ) -> Dict[str, float]:
        """
        Return explicit term-structure diagnostics.

        The output is designed for dashboards and release notes, not just regime
        classification.
        """
        for label, value in (
            ("front_target", front_target),
            ("anchor_target", anchor_target),
            ("back_target", back_target),
        ):
            if value <= 0:
                raise ValueError(f"{label} must be positive")

        iv_front = self._nearest_iv(front_target)
        iv_anchor = self._nearest_iv(anchor_target)
        iv_back = self._nearest_iv(back_target)

        x = np.asarray(self.atm_term_structure.index, dtype=float)
        y = np.asarray(self.atm_term_structure.values, dtype=float)
        slope_per_year = 0.0
        slope_per_log_maturity = 0.0
        if x.size >= 2 and not np.allclose(x, x[0]):
            slope_per_year = float(np.polyfit(x, y, 1)[0])
            log_x = np.log(x)
            if not np.allclose(log_x, log_x[0]):
                slope_per_log_maturity = float(np.polyfit(log_x, y, 1)[0])

        return {
            "iv_front": iv_front,
            "iv_anchor": iv_anchor,
            "iv_back": iv_back,
            "front_to_anchor_ratio": float(iv_front / iv_anchor),
            "anchor_to_back_ratio": float(iv_anchor / iv_back),
            "front_minus_anchor": float(iv_front - iv_anchor),
            "anchor_minus_back": float(iv_anchor - iv_back),
            "slope_per_year": slope_per_year,
            "slope_per_log_maturity": slope_per_log_maturity,
            "curvature": float(iv_front - 2.0 * iv_anchor + iv_back),
        }

    def skew_term_metrics(
        self,
        front_target: float = 7.0 / 365.0,
        anchor_target: float = 30.0 / 365.0,
        back_target: float = 90.0 / 365.0,
    ) -> Dict[str, float | None]:
        """Return skew diagnostics across the term structure."""
        if self.skew_by_maturity is None or self.skew_by_maturity.empty:
            return {
                "skew_front": None,
                "skew_anchor": None,
                "skew_back": None,
                "skew_front_minus_anchor": None,
                "skew_anchor_minus_back": None,
                "skew_slope_per_year": None,
            }

        skew_front = self._nearest_skew(front_target)
        skew_anchor = self._nearest_skew(anchor_target)
        skew_back = self._nearest_skew(back_target)

        x = np.asarray(self.skew_by_maturity.index, dtype=float)
        y = np.asarray(self.skew_by_maturity.values, dtype=float)
        skew_slope = 0.0
        if x.size >= 2 and not np.allclose(x, x[0]):
            skew_slope = float(np.polyfit(x, y, 1)[0])

        return {
            "skew_front": skew_front,
            "skew_anchor": skew_anchor,
            "skew_back": skew_back,
            "skew_front_minus_anchor": float(skew_front - skew_anchor),
            "skew_anchor_minus_back": float(skew_anchor - skew_back),
            "skew_slope_per_year": skew_slope,
        }

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

    def summary(
        self,
        *,
        hv_30d: float | None = None,
        lookback_days: int = 252,
    ) -> Dict[str, float | str | None]:
        """
        Return a report-ready analytics snapshot.

        Optional inputs enrich the result with IV percentile and IV-vs-RV premium.
        """
        summary: Dict[str, float | str | None] = {
            **self.term_structure_metrics(),
            **self.skew_term_metrics(),
            **self.trading_signal(),
        }
        summary["iv_percentile"] = (
            self.iv_percentile(lookback_days=lookback_days)
            if self.historical_atm_iv is not None and not self.historical_atm_iv.empty
            else None
        )
        summary["vol_premium"] = self.vol_premium(hv_30d) if hv_30d is not None else None
        return summary
