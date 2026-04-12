"""Portfolio analytics, stress testing, and scenario-based tail-risk helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from .black_scholes import BlackScholesModel, OptionParameters, OptionType
from .greeks_calculator import GreeksCalculator


def _weighted_average(values: Sequence[float], weights: Sequence[float]) -> float:
    arr = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    if arr.size == 0:
        return 0.0
    if float(np.abs(w).sum()) == 0.0:
        return float(arr.mean())
    return float(np.average(arr, weights=np.abs(w)))


@dataclass(frozen=True)
class PortfolioPosition:
    """Normalized portfolio position definition."""

    quantity: float
    spot_price: float
    strike_price: float
    time_to_maturity: float
    volatility: float
    option_type: str
    underlying: str = "UNKNOWN"
    is_coin_based: bool = False
    risk_free_rate: float = 0.05
    dividend_yield: float = 0.0
    label: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any], *, fallback_label: str | None = None) -> "PortfolioPosition":
        """Build a validated position from a mapping input."""
        option_type = str(data["option_type"]).lower()
        if option_type not in {"call", "put"}:
            raise ValueError("option_type must be 'call' or 'put'")
        position = cls(
            quantity=float(data["quantity"]),
            spot_price=float(data["spot_price"]),
            strike_price=float(data["strike_price"]),
            time_to_maturity=float(data["time_to_maturity"]),
            volatility=float(data["volatility"]),
            option_type=option_type,
            underlying=str(data.get("underlying", "UNKNOWN")).upper(),
            is_coin_based=bool(data.get("is_coin_based", False)),
            risk_free_rate=float(data.get("risk_free_rate", 0.05)),
            dividend_yield=float(data.get("dividend_yield", 0.0)),
            label=None if data.get("label") is None else str(data["label"]),
        )
        if position.label is None and fallback_label is not None:
            return cls(**{**position.to_dict(), "label": fallback_label})
        return position

    def to_dict(self) -> dict[str, Any]:
        """Convert to a plain dictionary compatible with existing helpers."""
        return {
            "quantity": self.quantity,
            "spot_price": self.spot_price,
            "strike_price": self.strike_price,
            "time_to_maturity": self.time_to_maturity,
            "volatility": self.volatility,
            "option_type": self.option_type,
            "underlying": self.underlying,
            "is_coin_based": self.is_coin_based,
            "risk_free_rate": self.risk_free_rate,
            "dividend_yield": self.dividend_yield,
            "label": self.label,
        }


@dataclass(frozen=True)
class PortfolioDistribution:
    """Tail-risk summary from scenario simulation."""

    confidence: float
    horizon_days: int
    base_portfolio_value: float
    expected_pnl: float
    value_at_risk: float
    conditional_value_at_risk: float
    worst_pnl: float
    spot_volatility: float
    vol_of_vol: float
    scenario_count: int

    def to_dict(self) -> dict[str, float | int]:
        return {
            "confidence": self.confidence,
            "horizon_days": self.horizon_days,
            "base_portfolio_value": self.base_portfolio_value,
            "expected_pnl": self.expected_pnl,
            "value_at_risk": self.value_at_risk,
            "conditional_value_at_risk": self.conditional_value_at_risk,
            "worst_pnl": self.worst_pnl,
            "spot_volatility": self.spot_volatility,
            "vol_of_vol": self.vol_of_vol,
            "scenario_count": self.scenario_count,
        }


@dataclass
class PortfolioReport:
    """Structured portfolio report with base, stress, and tail-risk views."""

    portfolio_summary: dict[str, Any]
    risk_metrics: dict[str, Any]
    concentration: dict[str, Any]
    positions: pd.DataFrame
    stress_tests: pd.DataFrame
    risk_distribution: PortfolioDistribution

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_summary": self.portfolio_summary,
            "risk_metrics": self.risk_metrics,
            "concentration": self.concentration,
            "positions": self.positions.to_dict(orient="records"),
            "stress_tests": self.stress_tests.to_dict(orient="records"),
            "risk_distribution": self.risk_distribution.to_dict(),
        }


class PortfolioAnalyzer:
    """Higher-level portfolio analytics built on top of the pricing engine."""

    def __init__(
        self,
        bs_model: BlackScholesModel | None = None,
        greeks_calculator: GreeksCalculator | None = None,
    ) -> None:
        self.bs_model = bs_model or BlackScholesModel()
        self.greeks_calculator = greeks_calculator or GreeksCalculator(self.bs_model)

    def _normalize_positions(
        self,
        positions: Sequence[PortfolioPosition | Mapping[str, Any]],
    ) -> list[PortfolioPosition]:
        normalized: list[PortfolioPosition] = []
        for index, position in enumerate(positions, start=1):
            if isinstance(position, PortfolioPosition):
                normalized.append(position)
            else:
                normalized.append(
                    PortfolioPosition.from_mapping(position, fallback_label=f"position_{index}")
                )
        return normalized

    def _to_option_parameters(
        self,
        position: PortfolioPosition,
        *,
        spot_price: float | None = None,
        volatility: float | None = None,
        time_to_maturity: float | None = None,
    ) -> OptionParameters:
        return OptionParameters(
            spot_price=float(position.spot_price if spot_price is None else spot_price),
            strike_price=position.strike_price,
            time_to_maturity=float(
                position.time_to_maturity if time_to_maturity is None else time_to_maturity
            ),
            volatility=float(position.volatility if volatility is None else volatility),
            risk_free_rate=position.risk_free_rate,
            dividend_yield=position.dividend_yield,
            option_type=OptionType.CALL if position.option_type == "call" else OptionType.PUT,
            is_coin_based=position.is_coin_based,
        )

    def _value_position(
        self,
        position: PortfolioPosition,
        *,
        spot_price: float | None = None,
        volatility: float | None = None,
        time_to_maturity: float | None = None,
    ) -> float:
        shocked_spot = float(position.spot_price if spot_price is None else spot_price)
        shocked_vol = float(position.volatility if volatility is None else volatility)
        shocked_ttm = float(
            position.time_to_maturity if time_to_maturity is None else time_to_maturity
        )

        if shocked_ttm <= 0:
            if position.option_type == "call":
                usd_price = max(shocked_spot - position.strike_price, 0.0)
            else:
                usd_price = max(position.strike_price - shocked_spot, 0.0)
            option_value = usd_price / shocked_spot if position.is_coin_based else usd_price
        else:
            pricing = self.bs_model.calculate_option_price(
                self._to_option_parameters(
                    position,
                    spot_price=shocked_spot,
                    volatility=shocked_vol,
                    time_to_maturity=shocked_ttm,
                )
            )
            option_value = pricing.coin_based_price if position.is_coin_based else pricing.usd_price
        if option_value is None:
            raise ValueError("Could not compute position value")
        if position.is_coin_based:
            return float(option_value) * shocked_spot * position.quantity
        return float(option_value) * position.quantity

    def position_breakdown(
        self,
        positions: Sequence[PortfolioPosition | Mapping[str, Any]],
    ) -> pd.DataFrame:
        """Return position-level price and Greek breakdown."""
        normalized = self._normalize_positions(positions)
        rows: list[dict[str, Any]] = []
        for index, position in enumerate(normalized, start=1):
            pricing = self.bs_model.calculate_option_price(self._to_option_parameters(position))
            label = position.label or f"position_{index}"
            position_value = self._value_position(position)
            rows.append(
                {
                    "label": label,
                    "underlying": position.underlying,
                    "option_type": position.option_type,
                    "quantity": position.quantity,
                    "spot_price": position.spot_price,
                    "strike_price": position.strike_price,
                    "time_to_maturity": position.time_to_maturity,
                    "days_to_maturity": position.time_to_maturity * 365.0,
                    "volatility": position.volatility,
                    "risk_free_rate": position.risk_free_rate,
                    "dividend_yield": position.dividend_yield,
                    "is_coin_based": position.is_coin_based,
                    "option_price": pricing.option_price,
                    "usd_price": pricing.usd_price,
                    "coin_based_price": pricing.coin_based_price,
                    "delta_usd": pricing.delta_usd,
                    "delta_coin": pricing.delta_coin,
                    "gamma": pricing.gamma,
                    "theta": pricing.theta,
                    "vega": pricing.vega,
                    "rho": pricing.rho,
                    "intrinsic_value": pricing.intrinsic_value,
                    "time_value": pricing.time_value,
                    "position_value": position_value,
                    "abs_position_value": abs(position_value),
                }
            )
        return pd.DataFrame(rows)

    def concentration_summary(
        self,
        positions: Sequence[PortfolioPosition | Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Return simple concentration metrics from absolute position values."""
        breakdown = self.position_breakdown(positions)
        if breakdown.empty:
            return {
                "largest_position_pct": 0.0,
                "largest_underlying_pct": 0.0,
                "largest_expiry_bucket_pct": 0.0,
                "abs_value_by_underlying": {},
                "abs_value_by_expiry": {},
            }

        total_abs = float(breakdown["abs_position_value"].sum())
        expiry_buckets = (
            breakdown.assign(expiry_bucket=breakdown["days_to_maturity"].round().astype(int).astype(str) + "d")
            .groupby("expiry_bucket")["abs_position_value"]
            .sum()
            .sort_values(ascending=False)
        )
        by_underlying = (
            breakdown.groupby("underlying")["abs_position_value"].sum().sort_values(ascending=False)
        )
        largest_position_pct = float(breakdown["abs_position_value"].max() / total_abs) if total_abs else 0.0
        largest_underlying_pct = float(by_underlying.iloc[0] / total_abs) if total_abs else 0.0
        largest_expiry_pct = float(expiry_buckets.iloc[0] / total_abs) if total_abs else 0.0
        return {
            "largest_position_pct": largest_position_pct,
            "largest_underlying_pct": largest_underlying_pct,
            "largest_expiry_bucket_pct": largest_expiry_pct,
            "abs_value_by_underlying": {str(k): float(v) for k, v in by_underlying.items()},
            "abs_value_by_expiry": {str(k): float(v) for k, v in expiry_buckets.items()},
        }

    def stress_test(
        self,
        positions: Sequence[PortfolioPosition | Mapping[str, Any]],
        *,
        spot_shocks: Sequence[float] = (-0.20, -0.10, 0.0, 0.10, 0.20),
        vol_shocks: Sequence[float] = (-0.15, 0.0, 0.15),
        days_forward: int = 1,
    ) -> pd.DataFrame:
        """
        Reprice the portfolio across spot/vol stress scenarios.

        ``spot_shocks`` are fractional spot moves.
        ``vol_shocks`` are absolute annualized volatility shifts.
        """
        if days_forward < 0:
            raise ValueError("days_forward must be >= 0")
        normalized = self._normalize_positions(positions)
        if not normalized:
            return pd.DataFrame(
                columns=[
                    "scenario",
                    "spot_shock",
                    "vol_shock",
                    "days_forward",
                    "base_value",
                    "shocked_value",
                    "pnl",
                    "pnl_pct",
                ]
            )

        base_value = float(self.position_breakdown(normalized)["position_value"].sum())
        results: list[dict[str, Any]] = []
        for spot_shock in spot_shocks:
            for vol_shock in vol_shocks:
                shocked_value = 0.0
                for position in normalized:
                    shocked_spot = max(position.spot_price * (1.0 + float(spot_shock)), 1e-12)
                    shocked_vol = max(position.volatility + float(vol_shock), 1e-6)
                    shocked_ttm = max(position.time_to_maturity - days_forward / 365.0, 0.0)
                    shocked_value += self._value_position(
                        position,
                        spot_price=shocked_spot,
                        volatility=shocked_vol,
                        time_to_maturity=shocked_ttm,
                    )
                pnl = shocked_value - base_value
                pnl_pct = 0.0 if abs(base_value) < 1e-12 else pnl / abs(base_value)
                results.append(
                    {
                        "scenario": (
                            f"spot_{spot_shock:+.0%}_vol_{vol_shock * 100:+.0f}pt"
                            f"_t+{days_forward}d"
                        ),
                        "spot_shock": float(spot_shock),
                        "vol_shock": float(vol_shock),
                        "days_forward": days_forward,
                        "base_value": base_value,
                        "shocked_value": shocked_value,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                    }
                )
        return pd.DataFrame(results).sort_values(["spot_shock", "vol_shock"]).reset_index(drop=True)

    def estimate_var_cvar(
        self,
        positions: Sequence[PortfolioPosition | Mapping[str, Any]],
        *,
        confidence: float = 0.95,
        horizon_days: int = 1,
        n_scenarios: int = 5000,
        random_seed: int = 7,
        spot_volatility: float | None = None,
        vol_of_vol: float = 0.25,
        spot_vol_correlation: float = -0.25,
    ) -> PortfolioDistribution:
        """Estimate VaR/CVaR from full repricing under sampled spot/volatility scenarios."""
        if not 0.0 < confidence < 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if horizon_days <= 0:
            raise ValueError("horizon_days must be positive")
        if n_scenarios <= 0:
            raise ValueError("n_scenarios must be positive")
        if not -1.0 <= spot_vol_correlation <= 1.0:
            raise ValueError("spot_vol_correlation must be between -1 and 1")

        normalized = self._normalize_positions(positions)
        if not normalized:
            return PortfolioDistribution(
                confidence=confidence,
                horizon_days=horizon_days,
                base_portfolio_value=0.0,
                expected_pnl=0.0,
                value_at_risk=0.0,
                conditional_value_at_risk=0.0,
                worst_pnl=0.0,
                spot_volatility=0.0,
                vol_of_vol=vol_of_vol,
                scenario_count=n_scenarios,
            )

        base_value = float(self.position_breakdown(normalized)["position_value"].sum())
        if spot_volatility is None:
            spot_volatility = _weighted_average(
                [position.volatility for position in normalized],
                [position.quantity * position.spot_price for position in normalized],
            )

        dt = horizon_days / 365.0
        rng = np.random.default_rng(random_seed)
        sqrt_dt = np.sqrt(dt)
        shock_by_underlying: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for underlying in sorted({position.underlying for position in normalized}):
            z_spot = rng.standard_normal(n_scenarios)
            z_vol = rng.standard_normal(n_scenarios)
            correlated_vol = (
                spot_vol_correlation * z_spot
                + np.sqrt(max(1.0 - spot_vol_correlation**2, 0.0)) * z_vol
            )
            shock_by_underlying[underlying] = (
                spot_volatility * sqrt_dt * z_spot,
                vol_of_vol * sqrt_dt * correlated_vol,
            )

        pnl = np.empty(n_scenarios, dtype=float)
        for scenario_idx in range(n_scenarios):
            shocked_value = 0.0
            for position in normalized:
                spot_return, vol_shift = shock_by_underlying[position.underlying]
                shocked_spot = max(
                    position.spot_price * (1.0 + float(spot_return[scenario_idx])),
                    1e-12,
                )
                shocked_vol = max(
                    position.volatility + float(vol_shift[scenario_idx]),
                    1e-6,
                )
                shocked_ttm = max(position.time_to_maturity - horizon_days / 365.0, 0.0)
                shocked_value += self._value_position(
                    position,
                    spot_price=shocked_spot,
                    volatility=shocked_vol,
                    time_to_maturity=shocked_ttm,
                )
            pnl[scenario_idx] = shocked_value - base_value

        cutoff = float(np.quantile(pnl, 1.0 - confidence))
        tail = pnl[pnl <= cutoff]
        value_at_risk = max(0.0, -cutoff)
        conditional_value_at_risk = max(
            0.0,
            -float(tail.mean()) if tail.size else -cutoff,
        )
        return PortfolioDistribution(
            confidence=confidence,
            horizon_days=horizon_days,
            base_portfolio_value=base_value,
            expected_pnl=float(pnl.mean()),
            value_at_risk=float(value_at_risk),
            conditional_value_at_risk=float(conditional_value_at_risk),
            worst_pnl=float(pnl.min()),
            spot_volatility=float(spot_volatility),
            vol_of_vol=float(vol_of_vol),
            scenario_count=n_scenarios,
        )

    def build_report(
        self,
        positions: Sequence[PortfolioPosition | Mapping[str, Any]],
        *,
        stress_spot_shocks: Sequence[float] = (-0.20, -0.10, 0.0, 0.10, 0.20),
        stress_vol_shocks: Sequence[float] = (-0.15, 0.0, 0.15),
        stress_days_forward: int = 1,
        confidence: float = 0.95,
        horizon_days: int = 1,
        n_scenarios: int = 5000,
        random_seed: int = 7,
        spot_volatility: float | None = None,
        vol_of_vol: float = 0.25,
        spot_vol_correlation: float = -0.25,
    ) -> PortfolioReport:
        """Build a combined portfolio report with base, stress, and tail-risk views."""
        normalized = self._normalize_positions(positions)
        position_dicts = [position.to_dict() for position in normalized]
        portfolio = self.greeks_calculator.calculate_portfolio_greeks(position_dicts)
        risk_metrics = self.greeks_calculator.calculate_risk_metrics(position_dicts)
        positions_df = self.position_breakdown(normalized)
        stress_df = self.stress_test(
            normalized,
            spot_shocks=stress_spot_shocks,
            vol_shocks=stress_vol_shocks,
            days_forward=stress_days_forward,
        )
        distribution = self.estimate_var_cvar(
            normalized,
            confidence=confidence,
            horizon_days=horizon_days,
            n_scenarios=n_scenarios,
            random_seed=random_seed,
            spot_volatility=spot_volatility,
            vol_of_vol=vol_of_vol,
            spot_vol_correlation=spot_vol_correlation,
        )
        return PortfolioReport(
            portfolio_summary=portfolio.get_summary(),
            risk_metrics={
                "gamma_exposure": risk_metrics.gamma_exposure,
                "gamma_flip_point": risk_metrics.gamma_flip_point,
                "max_gamma_strike": risk_metrics.max_gamma_strike,
                "pin_risk": risk_metrics.pin_risk,
                "vega_exposure": risk_metrics.vega_exposure,
                "theta_decay_daily": risk_metrics.theta_decay_daily,
                "delta_neutral_hedge": risk_metrics.delta_neutral_hedge,
            },
            concentration=self.concentration_summary(normalized),
            positions=positions_df,
            stress_tests=stress_df,
            risk_distribution=distribution,
        )


def stress_test_portfolio(
    positions: Sequence[PortfolioPosition | Mapping[str, Any]],
    **kwargs: Any,
) -> pd.DataFrame:
    """Convenience wrapper for portfolio stress tests."""
    return PortfolioAnalyzer().stress_test(positions, **kwargs)


def build_portfolio_report(
    positions: Sequence[PortfolioPosition | Mapping[str, Any]],
    **kwargs: Any,
) -> dict[str, Any]:
    """Convenience wrapper returning a JSON-friendly portfolio report."""
    return PortfolioAnalyzer().build_report(positions, **kwargs).to_dict()
