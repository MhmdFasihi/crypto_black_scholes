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
surface.fit(chain[["strike", "time_to_maturity", "implied_volatility"]])
print(surface.get_atm_iv(30 / 365))
```

## Next reads

- [Core Concepts](core-concepts.md)
- [Pricing Guide](pricing-guide.md)
- [Data and Market Inputs](data-and-market-inputs.md)
