# Crypto Black-Scholes

A Python library for pricing coin-settled cryptocurrency options using the Black-76 model adapted for futures.

## Features

- Pricing of European call and put options using **Black-76 model** (appropriate for coin-settled options)
- Calculation of Greeks (Delta, Gamma, Vega, Theta, Rho)
- Breakeven price calculations
- Real-time data fetching from Deribit exchange
- Designed specifically for coin-settled options (no risk-free rate discounting)

## Model Details

This package uses the **Black-76 model** rather than standard Black-Scholes because:

- Coin-settled crypto options behave like futures options
- No risk-free rate (r=0) since settlement is in cryptocurrency
- Uses forward/futures price (F) instead of spot price (S)
- Premium and payoff are both in cryptocurrency units

## Differences from Standard Black-Scholes

- **Black-76 vs Black-Scholes**: Uses futures pricing instead of spot pricing
- **No risk-free rate**: r=0 throughout all calculations
- **Settlement**: All values in cryptocurrency units
- **Rho**: Always 0 (no interest rate sensitivity)

## Installation

```bash
pip install .
```

## Usage

```python
from crypto_bs import price_option, delta, gamma, vega, theta, rho, breakeven_price

# Price a call option
# F: forward price, K: strike, T: time to expiration (years), sigma: volatility
price = price_option(F=109000, K=105000, T=1/365, sigma=0.5, option_type='call')

# Calculate Greeks
d = delta(F=109000, K=105000, T=1/365, sigma=0.5, option_type='call')
g = gamma(F=109000, K=105000, T=1/365, sigma=0.5)
v = vega(F=109000, K=105000, T=1/365, sigma=0.5)

# Breakeven price
be = breakeven_price(K=105000, premium=price, option_type='call')
```

## Data Integration

Fetch real-time data from Deribit:

```python
from crypto_bs import get_btc_forward_price, get_option_data, get_available_instruments

# Get BTC forward price
F = get_btc_forward_price()

# Get option data
option_data = get_option_data('BTC-3SEP25-105000-C')
sigma = option_data['implied_volatility']
```

## License

MIT