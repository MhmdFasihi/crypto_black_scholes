# Volatility Analytics

## Historical volatility estimators

The package includes four realized-volatility estimators:

- `close_to_close_hv`
- `parkinson_hv`
- `rogers_satchell_hv`
- `yang_zhang_hv`

Example:

```python
import pandas as pd
from crypto_bs import close_to_close_hv, yang_zhang_hv

close = pd.Series([100, 102, 101, 104, 103, 106, 108])
open_ = close.shift(1).fillna(close.iloc[0])
high = close * 1.01
low = close * 0.99

hv_cc = close_to_close_hv(close, window=5)
hv_yz = yang_zhang_hv(open_, high, low, close, window=5)
```

## Regime analytics

`VolatilityAnalytics` consumes simple series objects so it can be used with or without a fitted surface:

```python
import pandas as pd
from crypto_bs import VolatilityAnalytics

term = pd.Series([0.85, 0.72, 0.65], index=[7 / 365, 30 / 365, 90 / 365])
skew = pd.Series([0.04, 0.035, 0.03], index=[7 / 365, 30 / 365, 90 / 365])

va = VolatilityAnalytics(atm_term_structure=term, skew_by_maturity=skew)
print(va.ts_regime())
print(va.skew_regime())
print(va.trading_signal())
```

You can also build analytics directly from a fitted surface:

```python
from crypto_bs import VolatilityAnalytics, VolatilitySurface

surface = VolatilitySurface()
surface.fit(chain_df)
va = VolatilityAnalytics.from_surface(surface)
print(va.ts_regime(), va.skew_regime())
```

## IV vs RV

To compare implied and realized volatility:

```python
from crypto_bs import get_btc_volatility

rv_30d = get_btc_volatility(days=90, window=30)
premium = va.vol_premium(rv_30d)
print(premium)
```
