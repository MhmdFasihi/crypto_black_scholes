# Crypto Black-Scholes

**Version 0.6.0** — Python library for pricing **coin-settled** cryptocurrency options with Black-76 and Black-Scholes-style models, Greeks, portfolio aggregation, Deribit-oriented helpers, historical volatility estimators, GEX/vol-regime analytics, an implied-volatility surface foundation, and a reusable market-data client.

See **[CHANGELOG.md](CHANGELOG.md)** for release notes and breaking changes.
See **[docs/README.md](docs/README.md)** for the local documentation index.

## Features

- **Pricing** — Black-76 (forward / coin premium), enhanced Black-Scholes with USD vs coin-denominated premium
- **Greeks** — Delta (USD vs coin premium), gamma, theta, vega, rho; second-order Greeks (speed, charm, vanna, vomma) via finite differences in `GreeksCalculator`
- **Portfolio** — Multi-position Greeks, risk metrics, gamma exposure profile
- **Data** — Deribit REST helpers, reusable `DeribitClient`, normalized chain/surface fetchers, CoinGecko-backed BTC spot and realized-vol helpers
- **IV** — Implied vol from market price (Brent’s method), intrinsic and bounds checks
- **Vectorized chain pricing** — `price_options_vectorized` for many strikes / expiries at once
- **Breakeven** — USD and coin-settled breakeven helpers
- **Historical volatility** — Close-to-close, Parkinson, Rogers-Satchell, Yang-Zhang estimators
- **GEX analytics** — Net gamma exposure by strike, cumulative GEX, gamma flip point
- **Volatility regimes** — Term-structure and skew regime classifier with simple signal synthesis
- **Volatility surface foundation** — Fit/interpolate IV over strike and maturity

## Model overview

1. **Black-76 (module-level `price_option`)** — Forward `F`, undiscounted coin premium; suited to Deribit-style quoting.
2. **`BlackScholesModel`** — Spot-based Merton BS; **`is_coin_based=True`** for premium as fraction of spot; exposes **`delta_usd`** (hedge delta) and **`delta_coin`** (premium sensitivity to spot).
3. **Portfolio** — Aggregations use **USD delta** per position for `total_delta` and dollar exposures.

## Installation

```bash
pip install -U crypto-bs
```

Import as:

```python
import crypto_bs
```

Requires Python ≥3.10, `numpy`, `scipy`, `pandas`, `requests` (see `pyproject.toml`).

## Documentation

- [Docs index](docs/README.md)
- [Getting started](docs/guides/getting-started.md)
- [Data and market inputs](docs/guides/data-and-market-inputs.md)
- [Volatility surface guide](docs/guides/volatility-surface.md)
- [Cookbook](docs/tutorials/cookbook.md)

## Upgrading from 0.1.x

- Replace **`result.delta`** with **`result.delta_usd`** (hedging / notional delta) and/or **`result.delta_coin`** (academic / premium-in-coin sensitivity).
- Dicts from **`price_coin_based_option`** / **`validate_deribit_pricing`**: use **`delta_usd`** / **`delta_coin`** instead of **`delta`**.
- **`get_btc_volatility()`** now computes realized volatility from CoinGecko daily closes; for exchange-specific studies, prefer feeding your own OHLC data into `crypto_bs.historical_vol`.
- Optional: add **`pytest`** to your environment for the test suite (`pip install pytest`).

## Quick start

```python
from crypto_bs import price_option, delta, gamma, price_options_vectorized
import numpy as np

# Black-76 coin premium
price = price_option(F=110000, K=105000, T=1/365, sigma=0.6, option_type='call')
print(f"Premium (coin): {price:.6f}")

d = delta(110000, 105000, 1/365, 0.6, 'call')
g = gamma(110000, 105000, 1/365, 0.6)

# Whole chain in one call
K = np.array([100000.0, 105000.0, 110000.0])
T = np.full(3, 1 / 365)
sig = np.full(3, 0.6)
types = np.array(["call", "call", "put"])
premiums = price_options_vectorized(110000, K, T, sig, types)
```

### Breakeven

```python
from crypto_bs import breakeven_price, breakeven_price_coin_based

be_usd = breakeven_price(105000, 500, 'call')
be_coin = breakeven_price_coin_based(105000, price, 'call')
```

## Advanced usage

### Coin-based `BlackScholesModel`

```python
from crypto_bs import BlackScholesModel, OptionParameters, OptionType

bs_model = BlackScholesModel()
params = OptionParameters(
    spot_price=110000,
    strike_price=105000,
    time_to_maturity=1/365,
    volatility=0.6,
    option_type=OptionType.CALL,
    is_coin_based=True,
)

result = bs_model.calculate_option_price(params)
print(f"Coin premium: {result.coin_based_price:.6f}")
print(f"USD equivalent: ${result.usd_price:.2f}")
print(f"Delta USD (hedge): {result.delta_usd:.6f}")
print(f"Delta coin premium: {result.delta_coin:.9f}")
```

### Portfolio risk

```python
from crypto_bs import analyze_portfolio_risk

portfolio = [
    {
        "quantity": 10,
        "spot_price": 110000,
        "strike_price": 105000,
        "time_to_maturity": 1/365,
        "volatility": 0.6,
        "option_type": "call",
        "underlying": "BTC",
        "is_coin_based": True,
    }
]

risk = analyze_portfolio_risk(portfolio)
print("Portfolio delta (USD):", risk["portfolio_summary"]["total_delta"])
print("Gamma exposure:", risk["risk_metrics"]["gamma_exposure"])
```

### Market data helpers

```python
from crypto_bs import (
    DeribitClient,
    get_btc_forward_price,
    get_option_data,
    validate_deribit_pricing,
)

F = get_btc_forward_price()
option_data = get_option_data("BTC-3SEP25-105000-C")
client = DeribitClient()
chain = client.get_full_chain(min_open_interest=100)
surface_input = client.get_iv_surface_data(min_open_interest=100)

validation = validate_deribit_pricing(
    deribit_price_btc=option_data["mark_price"],
    spot=F,
    strike=105000,
    time_to_maturity=1/365,
    option_type="call",
)
print("IV:", validation["implied_volatility"])
print("Delta USD:", validation["delta_usd"])
print("Chain rows:", len(chain))
print("Surface rows:", len(surface_input))
```

Requests use a **10-second timeout**; the client adds retries, short-lived caching, and lightweight pacing for repeated Deribit calls. Failures surface as `requests` exceptions or `ValueError` from the helpers.

### Historical volatility

```python
import pandas as pd
from crypto_bs import close_to_close_hv, get_btc_volatility, parkinson_hv, yang_zhang_hv

# Example OHLC arrays as pandas Series
close = pd.Series([100, 102, 101, 104, 103, 106, 108])
high = close * 1.01
low = close * 0.99
open_ = close.shift(1).fillna(close.iloc[0])

hv_cc = close_to_close_hv(close, window=5)
hv_parkinson = parkinson_hv(high, low, window=5)
hv_yz = yang_zhang_hv(open_, high, low, close, window=5)
btc_hv = get_btc_volatility(days=120, window=30)
```

### GEX and volatility analytics

```python
import pandas as pd
from crypto_bs import compute_gex, gex_summary, VolatilityAnalytics

chain = pd.DataFrame({
    "strike": [90000, 100000, 110000, 90000, 100000, 110000],
    "time_to_maturity": [30/365] * 6,
    "volatility": [0.7] * 6,
    "option_type": ["call", "call", "call", "put", "put", "put"],
    "open_interest": [1200, 1800, 900, 1400, 2000, 1300],
})
gex_df = compute_gex(chain, spot=100000)
print(gex_summary(gex_df, spot=100000))

term = pd.Series([0.85, 0.72, 0.65], index=[7/365, 30/365, 90/365])
skew = pd.Series([0.04, 0.035, 0.03], index=[7/365, 30/365, 90/365])
va = VolatilityAnalytics(atm_term_structure=term, skew_by_maturity=skew)
print(va.ts_regime(), va.skew_regime(), va.trading_signal())
```

### Volatility surface

```python
import pandas as pd
from crypto_bs import VolatilitySurface

chain = pd.DataFrame({
    "strike": [90000, 100000, 110000, 90000, 100000, 110000],
    "time_to_maturity": [30/365, 30/365, 30/365, 90/365, 90/365, 90/365],
    "implied_volatility": [0.74, 0.70, 0.73, 0.66, 0.62, 0.65],
})
surface = VolatilitySurface()
surface.fit(chain)
print(surface.get_iv(105000, 60/365))
print(surface.get_term_structure())
```

## API reference (summary)

| Symbol | Role |
|--------|------|
| `price_option`, `black_76_call`, `black_76_put` | Scalar Black-76 coin premium |
| `price_options_vectorized` | Vectorized chain pricing |
| `delta`, `gamma`, `vega`, `theta`, `rho` | Black-76 Greeks on forward `F`; `rho(..., risk_free_rate=0)` |
| `breakeven_price`, `breakeven_price_coin_based` | Breakeven spot levels |
| `BlackScholesModel`, `OptionParameters`, `OptionPricing` | Full pricing + Greeks; **`OptionPricing.delta_usd` / `delta_coin`** |
| `calculate_implied_volatility` | IV search; default max vol **20.0**; validates vs intrinsic |
| `GreeksCalculator`, `calculate_option_greeks`, `analyze_portfolio_risk` | Profiles and portfolio |
| `DeribitClient` | Reusable market-data client with retry/cache/pacing |
| `get_btc_forward_price`, `get_option_data`, `get_available_instruments`, `get_btc_price` | Market-data convenience wrappers |
| `get_full_chain`, `get_iv_surface_data` | Normalized chain and surface-input fetchers |
| `get_btc_volatility` | Realized volatility from CoinGecko daily closes |
| `close_to_close_hv`, `parkinson_hv`, `rogers_satchell_hv`, `yang_zhang_hv`, `vol_premium` | Historical volatility analytics |
| `compute_gex`, `find_gamma_flip`, `gex_summary` | Gamma exposure analytics |
| `VolatilityAnalytics` | Term structure/skew regimes and trading signal |
| `VolatilitySurface` | IV surface fit/interpolation and sanity checks |

Full signatures and defaults are in the source docstrings.

## Validation (example)

Using real Deribit-style numbers, model vs mark can be on the order of **~1%** in BTC premium depending on mark, forward, and IV; use `validate_deribit_pricing` and live `get_option_data` for your own checks.

## Testing

```bash
# From repo root (recommended)
pytest tests/ -v

# With conda
conda activate crypto-option
cd /path/to/crypto_bs_project
PYTHONPATH=. pytest tests/ -v

# Wrapper script
python run_tests.py
```

The suite includes **36** tests (pricing, Greeks, IV, historical vol, GEX, regime analytics, surface interpolation, and parity/data checks). Install **pytest** if it is not already in the environment.

## License and links

- License: see **LICENSE** in the repository.
- Repository: [github.com/MhmdFasihi/crypto_black_scholes](https://github.com/MhmdFasihi/crypto_black_scholes)
- **Changes / migration:** [CHANGELOG.md](CHANGELOG.md)

---

Built for cryptocurrency options workflows that need **coin-settled** premiums, explicit **hedge delta vs coin-premium delta**, and **portfolio** Greeks.
