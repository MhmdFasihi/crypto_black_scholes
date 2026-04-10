# Risk and Greeks

## Basic Greeks

For forward-based Black-76 helpers:

```python
from crypto_bs import delta, gamma, theta, vega, rho

d = delta(110000, 105000, 7 / 365, 0.62, "call")
g = gamma(110000, 105000, 7 / 365, 0.62)
t = theta(110000, 105000, 7 / 365, 0.62, "call")
v = vega(110000, 105000, 7 / 365, 0.62)
r = rho(110000, 105000, 7 / 365, 0.62, "call")
```

## Full Greeks profile

Use `calculate_option_greeks()` when you want the richer profile with second-order sensitivities:

```python
from crypto_bs import calculate_option_greeks

profile = calculate_option_greeks(
    spot=110000,
    strike=105000,
    time_to_maturity=7 / 365,
    volatility=0.62,
    option_type="call",
    is_coin_based=True,
)
print(profile["delta_usd"], profile["gamma"], profile["vanna"])
```

## Portfolio aggregation

```python
from crypto_bs import analyze_portfolio_risk

portfolio = [
    {
        "quantity": 5,
        "spot_price": 110000,
        "strike_price": 105000,
        "time_to_maturity": 7 / 365,
        "volatility": 0.62,
        "option_type": "call",
        "is_coin_based": True,
    }
]

risk = analyze_portfolio_risk(portfolio)
print(risk["portfolio_summary"]["total_delta"])
print(risk["risk_metrics"]["gamma_exposure"])
```

`analyze_portfolio_risk()` aggregates on USD delta, not coin delta.
