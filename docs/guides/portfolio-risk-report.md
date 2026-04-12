# Portfolio Risk Guide

## Overview

`crypto_bs.portfolio` adds a higher-level reporting layer on top of the existing pricing and Greeks engine. Use it when you want more than aggregate Greeks:

- position-level breakdowns
- concentration by underlying and expiry bucket
- full-repricing stress tests
- scenario-based VaR / CVaR estimates

## Build a report

```python
from crypto_bs import PortfolioAnalyzer

portfolio = [
    {
        "label": "btc_call",
        "quantity": 8,
        "spot_price": 100000,
        "strike_price": 105000,
        "time_to_maturity": 30 / 365,
        "volatility": 0.68,
        "option_type": "call",
        "underlying": "BTC",
        "is_coin_based": True,
    },
    {
        "label": "eth_call",
        "quantity": 15,
        "spot_price": 3500,
        "strike_price": 3600,
        "time_to_maturity": 45 / 365,
        "volatility": 0.80,
        "option_type": "call",
        "underlying": "ETH",
        "is_coin_based": True,
    },
]

analyzer = PortfolioAnalyzer()
report = analyzer.build_report(portfolio)

print(report.portfolio_summary)
print(report.risk_metrics)
print(report.concentration)
print(report.risk_distribution.to_dict())
```

## Position breakdown

```python
positions_df = analyzer.position_breakdown(portfolio)
print(positions_df[["label", "underlying", "position_value", "delta_usd", "gamma"]])
```

## Stress testing

```python
stress_df = analyzer.stress_test(
    portfolio,
    spot_shocks=(-0.20, -0.10, 0.0, 0.10, 0.20),
    vol_shocks=(-0.15, 0.0, 0.15),
    days_forward=1,
)
print(stress_df[["scenario", "pnl", "pnl_pct"]])
```

`spot_shocks` are fractional spot moves. `vol_shocks` are absolute annualized volatility shifts, so `0.15` means `+15` vol points.

## VaR / CVaR

```python
distribution = analyzer.estimate_var_cvar(
    portfolio,
    confidence=0.95,
    horizon_days=1,
    n_scenarios=5000,
    random_seed=7,
)
print(distribution.value_at_risk, distribution.conditional_value_at_risk)
```

This simulation reprices the portfolio under sampled spot and volatility shocks. It is useful for quick portfolio ranking and monitoring, but it is not a substitute for a full historical or pathwise risk engine.
