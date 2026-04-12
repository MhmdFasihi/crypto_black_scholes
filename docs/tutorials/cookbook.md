# Cookbook

## Recipe: Validate a live Deribit quote

```python
from crypto_bs import get_btc_forward_price, get_option_data, validate_deribit_pricing

forward = get_btc_forward_price()
quote = get_option_data("BTC-01MAY26-100000-C")

check = validate_deribit_pricing(
    deribit_price_btc=quote["mark_price"],
    spot=forward,
    strike=100000,
    time_to_maturity=21 / 365,
    option_type="call",
)
print(check)
```

## Recipe: Build a surface from exchange data

```python
from crypto_bs import DeribitClient, VolatilitySurface

client = DeribitClient()
surface_input = client.get_iv_surface_data(min_open_interest=100)

surface = VolatilitySurface()
surface.fit(surface_input[["strike", "time_to_maturity", "implied_volatility"]])
print(surface.get_term_structure())
print(surface.get_surface_grid(num_strikes=7).head())
print(surface.describe_surface().head())
```

## Recipe: Compare implied vol to realized vol

```python
from crypto_bs import DeribitClient, VolatilityAnalytics

client = DeribitClient()
surface_input = client.get_iv_surface_data(min_open_interest=100)

term = (
    surface_input.sort_values("time_to_maturity")
    .groupby("time_to_maturity")["implied_volatility"]
    .median()
)
analytics = VolatilityAnalytics(atm_term_structure=term)

rv = client.get_btc_volatility(days=120, window=30)
print(analytics.summary(hv_30d=rv))
```
