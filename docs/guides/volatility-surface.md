# Volatility Surface Guide

## Fit a surface

`VolatilitySurface` provides a lightweight interpolation layer over strike and maturity plus smile-oriented wing metrics, export-ready grids, and summary diagnostics:

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
grid = surface.get_surface_grid(maturities=[30 / 365, 60 / 365], num_strikes=5)
summary = surface.describe_surface()
skew = surface.get_skew(30 / 365)
rr = surface.get_risk_reversal(30 / 365)
bf = surface.get_butterfly(30 / 365)
checks = surface.check_arbitrage()
```

`check_arbitrage()` enforces **total variance monotonicity** (`T × σ²(T)` non-decreasing) as the calendar-spread no-arbitrage condition and a convexity check on each smile slice.

## Live input path

```python
from crypto_bs import DeribitClient

client = DeribitClient()
surface_input = client.get_iv_surface_data(min_open_interest=100)
surface.fit(surface_input)
```

## Visualize the surface (new in v1.0)

```python
from crypto_bs import (
    VolatilityAnalytics,
    plot_volatility_surface,
    plot_smile_slice,
    plot_term_structure,
)

# Interactive 3-D surface
fig = plot_volatility_surface(surface, num_strikes=40, title="BTC IV Surface")
fig.show()

# Smile curves — one line per fitted maturity
fig = plot_smile_slice(surface)
fig.show()

# ATM term structure with 25-delta skew overlay
analytics = VolatilityAnalytics.from_surface(surface)
fig = plot_term_structure(surface, analytics=analytics)
fig.show()
```

All three functions return `plotly.graph_objects.Figure`. Pass `template="plotly_white"` for a light theme.

## Scope

This release keeps the surface intentionally simple:

- Interpolation by strike within fitted maturities; linear interpolation across maturities.
- Export of long-form surface grids via `get_surface_grid()` for downstream analysis.
- Report-ready maturity summaries from `describe_surface()`.
- Delta-aware wing metrics when `underlying_price` and `option_type` are available in the input chain.
- Calendar and butterfly consistency checks.

It is not yet a parametrized SVI/SABR surface. Calibrated surface fitting is on the roadmap for v1.1.

## See also

- [Visualization Guide](visualization.md) — full reference for all four plot functions.
- [Volatility Analytics Guide](volatility-analytics.md) — regime classification and signal synthesis.
