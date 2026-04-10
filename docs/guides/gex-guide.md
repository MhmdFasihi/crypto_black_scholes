# GEX Guide

## Compute gamma exposure

```python
import pandas as pd
from crypto_bs import compute_gex

chain = pd.DataFrame(
    {
        "strike": [90000, 100000, 110000, 90000, 100000, 110000],
        "time_to_maturity": [30 / 365] * 6,
        "volatility": [0.70] * 6,
        "option_type": ["call", "call", "call", "put", "put", "put"],
        "open_interest": [1200, 1800, 900, 1400, 2000, 1300],
    }
)

gex = compute_gex(chain, spot=100000)
print(gex)
```

## Gamma flip and summary

```python
from crypto_bs import find_gamma_flip, gex_summary

flip = find_gamma_flip(gex)
summary = gex_summary(gex, spot=100000)

print(flip)
print(summary)
```

## Dealer convention

`compute_gex()` supports:

- `dealer_convention="short_gamma"`
- `dealer_convention="long_gamma"`

Use the one that matches your interpretation of dealer positioning.
