"""Implied volatility surface utilities and smile analytics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .black_scholes import BlackScholesModel, OptionParameters, OptionType


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
    _raw_by_t: Dict[float, pd.DataFrame] = field(default_factory=dict)
    _term: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    _spot: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))

    def _require_fitted(self) -> None:
        if not self._by_t:
            raise ValueError("surface not fitted")

    def fit(self, chain_df: pd.DataFrame) -> None:
        required = {"strike", "time_to_maturity", "implied_volatility"}
        optional = {"underlying_price", "option_type", "risk_free_rate", "dividend_yield"}
        missing = required.difference(chain_df.columns)
        if missing:
            raise ValueError(f"chain_df missing required columns: {sorted(missing)}")
        if chain_df.empty:
            raise ValueError("chain_df cannot be empty")

        columns = ["strike", "time_to_maturity", "implied_volatility"] + [
            column for column in ("underlying_price", "option_type", "risk_free_rate", "dividend_yield")
            if column in chain_df.columns
        ]
        clean = chain_df[columns].copy()
        clean = clean.dropna(subset=["strike", "time_to_maturity", "implied_volatility"])
        if (clean["implied_volatility"] <= 0).any():
            raise ValueError("implied_volatility must be positive")
        if "underlying_price" in clean.columns:
            valid_spot = clean["underlying_price"].dropna()
            if not valid_spot.empty and (valid_spot <= 0).any():
                raise ValueError("underlying_price must be positive when provided")
        if "option_type" in clean.columns:
            clean["option_type"] = clean["option_type"].astype(str).str.lower()
            if not clean["option_type"].isin({"call", "put"}).all():
                raise ValueError("option_type must be 'call' or 'put'")
        if "risk_free_rate" in clean.columns:
            clean["risk_free_rate"] = clean["risk_free_rate"].fillna(0.0)
        if "dividend_yield" in clean.columns:
            clean["dividend_yield"] = clean["dividend_yield"].fillna(0.0)

        self._by_t = {}
        self._raw_by_t = {}
        term = {}
        spot = {}
        for t, grp in clean.groupby("time_to_maturity"):
            raw = grp.sort_values(["strike"] + (["option_type"] if "option_type" in grp.columns else [])).reset_index(drop=True)
            aggregations: dict[str, Any] = {"implied_volatility": "mean"}
            if "underlying_price" in raw.columns:
                aggregations["underlying_price"] = "median"
            if "risk_free_rate" in raw.columns:
                aggregations["risk_free_rate"] = "mean"
            if "dividend_yield" in raw.columns:
                aggregations["dividend_yield"] = "mean"
            smile = raw.groupby("strike", as_index=False).agg(aggregations).sort_values("strike").reset_index(drop=True)
            t_float = float(t)
            self._raw_by_t[t_float] = raw
            self._by_t[t_float] = smile

            reference_spot = self._reference_spot_from_frame(raw)
            if reference_spot is not None:
                spot[t_float] = reference_spot
                atm_idx = (smile["strike"] - reference_spot).abs().idxmin()
            else:
                k_med = float(smile["strike"].median())
                atm_idx = (smile["strike"] - k_med).abs().idxmin()
            term[t_float] = float(smile.loc[atm_idx, "implied_volatility"])
        self._term = pd.Series(term).sort_index()
        self._spot = pd.Series(spot).sort_index()

    def _reference_spot_from_frame(self, frame: pd.DataFrame) -> float | None:
        if "underlying_price" not in frame.columns:
            return None
        valid = frame["underlying_price"].dropna()
        if valid.empty:
            return None
        return float(valid.median())

    def _interp_strike(self, t: float, strike: float) -> float:
        if t not in self._by_t:
            raise KeyError(f"time_to_maturity {t} not fitted")
        g = self._by_t[t]
        x = g["strike"].to_numpy(dtype=float)
        y = g["implied_volatility"].to_numpy(dtype=float)
        return float(np.interp(strike, x, y))

    def _nearest_time(self, time_to_maturity: float) -> float:
        self._require_fitted()
        return float(min(self._by_t.keys(), key=lambda t: abs(t - time_to_maturity)))

    def _reference_spot(self, time_to_maturity: float) -> float | None:
        if self._spot.empty:
            return None
        x = self._spot.index.to_numpy(dtype=float)
        y = self._spot.values.astype(float)
        return float(np.interp(time_to_maturity, x, y))

    def get_iv(self, strike: float, time_to_maturity: float) -> float:
        """Interpolate IV across strike, then linearly across maturities."""
        self._require_fitted()
        t_values = np.array(sorted(self._by_t.keys()), dtype=float)
        if len(t_values) == 1:
            return self._interp_strike(float(t_values[0]), strike)
        iv_at_t = np.array([self._interp_strike(float(t), strike) for t in t_values], dtype=float)
        return float(np.interp(time_to_maturity, t_values, iv_at_t))

    def get_atm_iv(self, time_to_maturity: float) -> float:
        """Return ATM IV from fitted term structure with linear interpolation."""
        self._require_fitted()
        x = self._term.index.to_numpy(dtype=float)
        y = self._term.values.astype(float)
        return float(np.interp(time_to_maturity, x, y))

    def get_term_structure(self) -> pd.Series:
        self._require_fitted()
        return self._term.copy()

    def get_smile_slice(
        self,
        time_to_maturity: float,
        num_points: int = 21,
        strike_grid: np.ndarray | list[float] | None = None,
    ) -> pd.DataFrame:
        """Return an interpolated smile slice with strike and moneyness columns."""
        self._require_fitted()
        nearest_t = self._nearest_time(time_to_maturity)
        nearest_slice = self._by_t[nearest_t]
        if strike_grid is None:
            strikes = nearest_slice["strike"].to_numpy(dtype=float)
            if num_points <= 0:
                raise ValueError("num_points must be positive")
            if len(strikes) == 1:
                strike_grid_arr = np.array([strikes[0]], dtype=float)
            else:
                strike_grid_arr = np.linspace(float(strikes.min()), float(strikes.max()), num_points)
            if len(strikes) > 1 and num_points == 1:
                spot = self._reference_spot(time_to_maturity)
                center = float(np.median(strikes)) if spot is None else float(spot)
                strike_grid_arr = np.array([center], dtype=float)
        else:
            strike_grid_arr = np.asarray(strike_grid, dtype=float)
            if strike_grid_arr.size == 0:
                raise ValueError("strike_grid cannot be empty")

        spot = self._reference_spot(time_to_maturity)
        smile = pd.DataFrame(
            {
                "strike": strike_grid_arr,
                "implied_volatility": [
                    self.get_iv(float(strike), time_to_maturity) for strike in strike_grid_arr
                ],
            }
        )
        if spot is None or spot <= 0:
            smile["moneyness"] = np.nan
            smile["log_moneyness"] = np.nan
        else:
            smile["moneyness"] = smile["strike"] / spot
            smile["log_moneyness"] = np.log(smile["strike"] / spot)
        return smile

    def get_surface_grid(
        self,
        maturities: np.ndarray | list[float] | None = None,
        strike_grid: np.ndarray | list[float] | None = None,
        num_strikes: int = 21,
    ) -> pd.DataFrame:
        """
        Return a plot-ready long-form surface grid.

        The returned DataFrame contains one row per strike / maturity pair with
        interpolated implied volatility plus moneyness diagnostics when a
        reference spot is available.
        """
        self._require_fitted()
        if maturities is None:
            maturity_grid = np.array(sorted(self._by_t.keys()), dtype=float)
        else:
            maturity_grid = np.asarray(maturities, dtype=float)
            if maturity_grid.size == 0:
                raise ValueError("maturities cannot be empty")
            maturity_grid = np.unique(maturity_grid.astype(float))

        if strike_grid is None:
            if num_strikes <= 0:
                raise ValueError("num_strikes must be positive")
            all_strikes = np.concatenate(
                [frame["strike"].to_numpy(dtype=float) for frame in self._by_t.values()]
            )
            if all_strikes.size == 1:
                strike_values = np.array([float(all_strikes[0])], dtype=float)
            else:
                strike_values = np.linspace(
                    float(all_strikes.min()),
                    float(all_strikes.max()),
                    num_strikes,
                )
        else:
            strike_values = np.asarray(strike_grid, dtype=float)
            if strike_values.size == 0:
                raise ValueError("strike_grid cannot be empty")

        frames: list[pd.DataFrame] = []
        for maturity in maturity_grid:
            slice_df = self.get_smile_slice(
                float(maturity),
                num_points=len(strike_values),
                strike_grid=strike_values,
            ).copy()
            slice_df.insert(0, "time_to_maturity", float(maturity))
            frames.append(slice_df)
        return pd.concat(frames, ignore_index=True)

    def describe_surface(
        self,
        maturities: np.ndarray | list[float] | None = None,
        delta: float = 0.25,
    ) -> pd.DataFrame:
        """
        Summarize the fitted surface by maturity.

        Each row combines ATM IV, wing metrics, strike coverage, and metadata
        about the nearest fitted maturity used for smile-wing extraction.
        """
        self._require_fitted()
        if maturities is None:
            maturity_grid = np.array(sorted(self._by_t.keys()), dtype=float)
        else:
            maturity_grid = np.asarray(maturities, dtype=float)
            if maturity_grid.size == 0:
                raise ValueError("maturities cannot be empty")
            maturity_grid = np.unique(maturity_grid.astype(float))

        rows: list[dict[str, float | int]] = []
        for maturity in maturity_grid:
            requested_t = float(maturity)
            nearest_t = self._nearest_time(requested_t)
            nearest_slice = self._by_t[nearest_t]
            nearest_raw = self._raw_by_t[nearest_t]
            spot = self._reference_spot(requested_t)
            metrics = self.get_smile_metrics(requested_t, delta=delta)
            rows.append(
                {
                    "time_to_maturity": requested_t,
                    "nearest_fitted_maturity": nearest_t,
                    "reference_spot": np.nan if spot is None else float(spot),
                    "atm_iv": float(self.get_atm_iv(requested_t)),
                    "put_iv": float(metrics["put_iv"]),
                    "call_iv": float(metrics["call_iv"]),
                    "put_strike": float(metrics["put_strike"]),
                    "call_strike": float(metrics["call_strike"]),
                    "skew": float(metrics["skew"]),
                    "risk_reversal": float(metrics["risk_reversal"]),
                    "butterfly": float(metrics["butterfly"]),
                    "strike_min": float(nearest_slice["strike"].min()),
                    "strike_max": float(nearest_slice["strike"].max()),
                    "quote_count": int(len(nearest_raw)),
                }
            )
        return pd.DataFrame(rows).sort_values("time_to_maturity").reset_index(drop=True)

    def _delta_metrics(self, time_to_maturity: float, delta: float) -> dict[str, float] | None:
        if not 0 < delta < 0.5:
            raise ValueError("delta must be between 0 and 0.5")
        nearest_t = self._nearest_time(time_to_maturity)
        frame = self._raw_by_t[nearest_t]
        if "option_type" not in frame.columns or "underlying_price" not in frame.columns:
            return None

        bs_model = BlackScholesModel()
        result: dict[str, float] = {"atm_iv": self.get_atm_iv(time_to_maturity)}
        for option_type, target_delta in (("call", delta), ("put", -delta)):
            subset = frame[frame["option_type"] == option_type]
            if subset.empty:
                return None
            best: tuple[float, float, float] | None = None
            for _, row in subset.iterrows():
                spot = row.get("underlying_price")
                if pd.isna(spot) or float(spot) <= 0:
                    continue
                params = OptionParameters(
                    spot_price=float(spot),
                    strike_price=float(row["strike"]),
                    time_to_maturity=float(nearest_t),
                    volatility=float(row["implied_volatility"]),
                    risk_free_rate=float(row.get("risk_free_rate", 0.0)),
                    dividend_yield=float(row.get("dividend_yield", 0.0)),
                    option_type=OptionType.CALL if option_type == "call" else OptionType.PUT,
                    is_coin_based=False,
                )
                row_delta = bs_model.calculate_option_price(params).delta_usd
                candidate = (
                    abs(row_delta - target_delta),
                    float(row["implied_volatility"]),
                    float(row["strike"]),
                )
                if best is None or candidate[0] < best[0]:
                    best = candidate
            if best is None:
                return None
            result[f"{option_type}_iv"] = best[1]
            result[f"{option_type}_strike"] = best[2]
        result["risk_reversal"] = result["call_iv"] - result["put_iv"]
        result["skew"] = result["put_iv"] - result["call_iv"]
        result["butterfly"] = 0.5 * (result["put_iv"] + result["call_iv"]) - result["atm_iv"]
        return result

    def get_smile_metrics(self, time_to_maturity: float, delta: float = 0.25) -> dict[str, float]:
        """
        Return smile metrics for the requested maturity.

        If the fitted data includes `underlying_price` and `option_type`, metrics
        are computed using nearest-delta wings. Otherwise a strike-quantile proxy
        is used as a fallback.
        """
        metrics = self._delta_metrics(time_to_maturity, delta)
        if metrics is not None:
            return metrics

        nearest_t = self._nearest_time(time_to_maturity)
        g = self._by_t[nearest_t]
        strikes = g["strike"].to_numpy(dtype=float)
        q_low = np.quantile(strikes, max(0.0, delta))
        q_high = np.quantile(strikes, min(1.0, 1 - delta))
        put_iv = self._interp_strike(float(nearest_t), float(q_low))
        call_iv = self._interp_strike(float(nearest_t), float(q_high))
        atm_iv = self.get_atm_iv(time_to_maturity)
        return {
            "put_iv": float(put_iv),
            "call_iv": float(call_iv),
            "put_strike": float(q_low),
            "call_strike": float(q_high),
            "atm_iv": float(atm_iv),
            "risk_reversal": float(call_iv - put_iv),
            "skew": float(put_iv - call_iv),
            "butterfly": float(0.5 * (put_iv + call_iv) - atm_iv),
        }

    def get_skew(self, time_to_maturity: float, delta: float = 0.25) -> float:
        """
        Return put-minus-call skew at the requested maturity.
        """
        return float(self.get_smile_metrics(time_to_maturity, delta=delta)["skew"])

    def get_risk_reversal(self, time_to_maturity: float, delta: float = 0.25) -> float:
        """Return call-minus-put risk reversal at the requested maturity."""
        return float(self.get_smile_metrics(time_to_maturity, delta=delta)["risk_reversal"])

    def get_butterfly(self, time_to_maturity: float, delta: float = 0.25) -> float:
        """Return the wing-average minus ATM butterfly metric."""
        return float(self.get_smile_metrics(time_to_maturity, delta=delta)["butterfly"])

    def check_arbitrage(self) -> Dict[str, List[str]]:
        """
        Basic consistency checks (not a full no-arbitrage proof).

        Butterfly proxy:
            Checks that the second finite difference of IV over strike is
            below a loose threshold.  A full static arbitrage check would
            require convexity of total variance in log-moneyness space; this
            is a lightweight heuristic only.

        Calendar check:
            Enforces that total variance T*sigma^2(T) is non-decreasing in T.
            This is the necessary condition for the absence of calendar-spread
            arbitrage: a shorter-dated option cannot be worth more than a
            longer-dated option at the same strike.
        """
        issues: Dict[str, List[str]] = {"butterfly": [], "calendar": []}
        if not self._by_t:
            return issues

        # --- butterfly proxy ---
        for t, g in self._by_t.items():
            iv = g["implied_volatility"].to_numpy(dtype=float)
            if len(iv) >= 3:
                second_diff = np.diff(iv, n=2)
                if np.any(np.abs(second_diff) > 0.35):
                    issues["butterfly"].append(
                        f"irregular smile curvature at T={t:.6f} "
                        f"(max |Δ²IV| = {float(np.abs(second_diff).max()):.4f})"
                    )

        # --- calendar check via total variance monotonicity ---
        if len(self._term) >= 2:
            ts_sorted = self._term.sort_index()
            t_vals = ts_sorted.index.to_numpy(dtype=float)
            iv_vals = ts_sorted.values.astype(float)
            total_var = t_vals * iv_vals ** 2
            diffs = np.diff(total_var)
            for i, d in enumerate(diffs):
                if d < -1e-6:
                    t0 = ts_sorted.index[i]
                    t1 = ts_sorted.index[i + 1]
                    issues["calendar"].append(
                        f"calendar arbitrage: total variance decreases from "
                        f"T={t0:.4f} ({total_var[i]:.6f}) to "
                        f"T={t1:.4f} ({total_var[i + 1]:.6f})"
                    )

        return issues
