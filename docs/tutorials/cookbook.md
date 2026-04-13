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

## Recipe: Interactive 3-D IV surface (new in v1.0)

```python
from crypto_bs import DeribitClient, VolatilitySurface, plot_volatility_surface

client = DeribitClient()
surface_input = client.get_iv_surface_data(min_open_interest=100)

surface = VolatilitySurface()
surface.fit(surface_input)

fig = plot_volatility_surface(surface, num_strikes=40, title="BTC IV Surface")
fig.show()                       # opens in browser
fig.write_html("btc_surface.html")  # save for sharing
```

## Recipe: Smile slices + term structure dashboard

```python
from crypto_bs import (
    VolatilityAnalytics,
    VolatilitySurface,
    plot_smile_slice,
    plot_term_structure,
)

surface = VolatilitySurface()
surface.fit(surface_input)
analytics = VolatilityAnalytics.from_surface(surface)

# Smile curves for near-term expirations
fig_smile = plot_smile_slice(surface, maturities=[7/365, 14/365, 30/365])
fig_smile.show()

# ATM term structure with 25-delta skew overlay
fig_ts = plot_term_structure(surface, analytics=analytics)
fig_ts.show()
```

## Recipe: GEX chart with gamma flip

```python
from crypto_bs import (
    DeribitClient,
    compute_gex,
    find_gamma_flip,
    get_btc_forward_price,
    plot_gex,
)

client = DeribitClient()
chain = client.get_full_chain(min_open_interest=50)
spot = get_btc_forward_price()

gex_df = compute_gex(chain, spot=spot)
flip = find_gamma_flip(gex_df)

fig = plot_gex(gex_df, spot=spot, gamma_flip=flip)
fig.show()
```
