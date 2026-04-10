# Pricing Guide

## Scalar Black-76 pricing

Use `price_option()` when you already have forward, strike, maturity, and IV:

```python
from crypto_bs import price_option

call_coin = price_option(110000, 105000, 14 / 365, 0.58, "call")
put_coin = price_option(110000, 105000, 14 / 365, 0.58, "put")
```

## Vectorized chain pricing

Use `price_options_vectorized()` for arrays of strikes, maturities, or vols:

```python
import numpy as np
from crypto_bs import price_options_vectorized

prices = price_options_vectorized(
    110000,
    np.array([100000.0, 105000.0, 110000.0]),
    np.full(3, 14 / 365),
    np.array([0.62, 0.60, 0.59]),
    np.array(["call", "call", "put"]),
)
```

## Full Black-Scholes workflow

Use `BlackScholesModel` when you want richer outputs and class-based parameter handling:

```python
from crypto_bs import BlackScholesModel, OptionParameters, OptionType

model = BlackScholesModel()
params = OptionParameters(
    spot_price=110000,
    strike_price=105000,
    time_to_maturity=14 / 365,
    volatility=0.58,
    option_type=OptionType.CALL,
    is_coin_based=True,
)
result = model.calculate_option_price(params)

print(result.coin_based_price)
print(result.delta_usd, result.delta_coin)
```

## Implied volatility

`BlackScholesModel.calculate_implied_volatility()` solves IV from market price and validates against intrinsic value:

```python
iv = model.calculate_implied_volatility(
    market_price=result.option_price,
    params=params,
)
```
