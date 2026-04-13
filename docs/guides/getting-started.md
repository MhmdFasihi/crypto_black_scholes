# Getting Started

`crypto_bs` is built around coin-settled crypto options workflows. The quickest path is:

```bash
pip install -U crypto-bs
```

Then import the package:

```python
import crypto_bs
```

## First price

```python
from crypto_bs import price_option

premium_coin = price_option(
    F=110000,
    K=105000,
    T=7 / 365,
    sigma=0.62,
    option_type="call",
)
print(premium_coin)
```

`price_option()` uses the Black-76 coin-premium convention that matches Deribit-style quoting.

## First Greeks

```python
from crypto_bs import delta, gamma, vega

d = delta(110000, 105000, 7 / 365, 0.62, "call")
g = gamma(110000, 105000, 7 / 365, 0.62)
v = vega(110000, 105000, 7 / 365, 0.62)
```

## First surface workflow

```python
from crypto_bs import DeribitClient, VolatilitySurface

client = DeribitClient()
chain = client.get_iv_surface_data(min_open_interest=100)

surface = VolatilitySurface()
surface.fit(chain)
print(surface.get_atm_iv(30 / 365))
```

## First interactive plot (new in v1.0)

```python
from crypto_bs import plot_volatility_surface

fig = plot_volatility_surface(surface)
fig.show()          # opens in browser
fig.write_html("surface.html")  # save to file
```

All four visualization functions (`plot_volatility_surface`, `plot_smile_slice`, `plot_term_structure`, `plot_gex`) return a `plotly.graph_objects.Figure`. No `.show()` is called inside the library.

## Next reads

- [Core Concepts](core-concepts.md)
- [Pricing Guide](pricing-guide.md)
- [Data and Market Inputs](data-and-market-inputs.md)
- [Visualization Guide](visualization.md)
