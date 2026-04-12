# Volatility Surface Guide

## Fit a surface

`VolatilitySurface` now provides a lightweight interpolation layer over strike and maturity plus smile-oriented wing metrics:

```python
import pandas as pd
from crypto_bs import VolatilitySurface

chain = pd.DataFrame(
    {
        "strike": [90000, 100000, 110000, 90000, 100000, 110000],
        "time_to_maturity": [30 / 365, 30 / 365, 30 / 365, 90 / 365, 90 / 365, 90 / 365],
        "implied_volatility": [0.74, 0.70, 0.73, 0.66, 0.62, 0.65],
        "underlying_price": [100000] * 6,
        "option_type": ["put", "call", "call", "put", "call", "call"],
    }
)

surface = VolatilitySurface()
surface.fit(chain)
```

## Query the surface

```python
iv = surface.get_iv(105000, 60 / 365)
atm = surface.get_atm_iv(30 / 365)
term = surface.get_term_structure()
smile = surface.get_smile_slice(30 / 365, num_points=7)
skew = surface.get_skew(30 / 365)
rr = surface.get_risk_reversal(30 / 365)
bf = surface.get_butterfly(30 / 365)
checks = surface.check_arbitrage()
```

## Live input path

For a live-ish build pipeline:

```python
from crypto_bs import DeribitClient

client = DeribitClient()
surface_input = client.get_iv_surface_data(min_open_interest=100)
surface.fit(surface_input[["strike", "time_to_maturity", "implied_volatility"]])
```

## Scope

This release keeps the surface intentionally simple:

- interpolation by strike within fitted maturities
- linear interpolation across maturities
- delta-aware wing metrics when `underlying_price` and `option_type` are available
- basic smile and calendar consistency checks

It is not yet a parametrized SVI/SABR surface.
