# Data and Market Inputs

## Convenience wrappers

The package keeps simple module-level helpers:

- `get_btc_forward_price()`
- `get_option_data(instrument_name)`
- `get_available_instruments(currency="BTC", kind="option")`
- `get_btc_price()`
- `get_btc_volatility(days=90, window=30, trading_days=365)`

These now delegate to a shared client implementation introduced in `0.6.0`.

## `DeribitClient`

`DeribitClient` is the reusable market-data entrypoint:

```python
from crypto_bs import DeribitClient

client = DeribitClient()
forward = client.get_btc_forward_price()
option = client.get_option_data("BTC-01MAY26-100000-C")
instruments = client.get_available_instruments()
```

Behavior:

- `timeout=10` seconds by default
- retry-enabled GET requests for transient failures
- lightweight pacing for repeated Deribit calls
- short-lived in-memory caching for repeated reads

## Full chain fetch

```python
chain = client.get_full_chain(currency="BTC", min_open_interest=100)
print(chain.columns.tolist())
```

Returned columns include:

- `instrument_name`
- `strike`
- `option_type`
- `expiry`
- `time_to_maturity`
- `underlying_price`
- `mark_price`
- `mid_price`
- `implied_volatility`
- `open_interest`

## IV surface input fetch

```python
surface_df = client.get_iv_surface_data(currency="BTC", min_open_interest=100)
```

This is the normalized slice intended for `VolatilitySurface.fit()`.

## BTC realized volatility

```python
rv = client.get_btc_volatility(days=120, window=30)
```

This uses CoinGecko daily closes and the package’s `close_to_close_hv()` estimator. For exchange-specific or intraday realized vol, bring your own OHLC data and use `crypto_bs.historical_vol` directly.
