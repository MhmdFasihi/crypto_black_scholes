# Crypto Black-Scholes

A comprehensive Python library for pricing coin-settled cryptocurrency options using advanced Black-Scholes and Black-76 models.

## 🚀 Features

- **Multiple Pricing Models**: Black-Scholes, Black-76, and coin-based adaptations
- **Complete Greeks Calculation**: Delta, Gamma, Theta, Vega, Rho + second-order Greeks (Speed, Charm, Vanna, Vomma)
- **Portfolio Risk Analysis**: Multi-position portfolio Greeks and risk metrics
- **Real-time Data Integration**: Live data from Deribit exchange
- **Coin-Settled Options Support**: Premiums and payoffs in cryptocurrency units
- **Breakeven Analysis**: Accurate breakeven calculations for coin-settled options
- **Implied Volatility**: Calculate IV from market prices
- **Advanced Validation**: Compare model prices with exchange data

## 📊 Model Details

This package implements **three pricing approaches** optimized for cryptocurrency options:

### 1. Black-76 Model (Primary for Coin-Settled)
- Designed for futures options (perfect for coin-settled crypto options)
- Uses forward/futures price instead of spot price
- No risk-free rate discounting (r=0)
- Premium and payoff in cryptocurrency units

### 2. Enhanced Black-Scholes
- Standard Black-Scholes with coin-based adaptations
- Supports both USD and cryptocurrency denominated options
- Advanced Greeks with second-order derivatives

### 3. Portfolio-Level Analysis
- Aggregate Greeks across multiple positions
- Risk metrics including gamma exposure and pin risk
- Greeks breakdown by underlying asset and expiry

## 💰 Coin-Settled Options Focus

**Key Differences from Standard Options:**
- **Premium**: Paid in cryptocurrency (e.g., 0.1 BTC for a $120K BTC option)
- **Settlement**: Payoff delivered in cryptocurrency
- **Pricing**: Uses Black-76 model with forward prices
- **Greeks**: Adjusted for cryptocurrency denomination
- **Breakeven**: Calculated in USD terms but based on crypto premium

## 📈 Installation

```bash
pip install .
```

## 🎯 Quick Start

```python
from crypto_bs import price_option, delta, gamma, breakeven_price, breakeven_price_coin_based

# Basic Black-76 pricing for coin-settled options
price = price_option(F=110000, K=105000, T=1/365, sigma=0.6, option_type='call')
print(f"Option Price: {price:.6f} BTC")

# Calculate Greeks
d = delta(110000, 105000, 1/365, 0.6, 'call')
g = gamma(110000, 105000, 1/365, 0.6)

# Breakeven analysis (USD premium)
be_usd = breakeven_price(105000, 500, 'call')
print(f"Breakeven (USD premium): ${be_usd:.2f}")

# Breakeven analysis (coin-settled premium)
be_coin = breakeven_price_coin_based(105000, price, 'call')
print(f"Breakeven (coin-based): ${be_coin:.2f}")
```

## 🔧 Advanced Usage

### Coin-Based Pricing with Full Analysis

```python
from crypto_bs import BlackScholesModel, OptionParameters, OptionType

# Advanced pricing with coin-based support
bs_model = BlackScholesModel()
params = OptionParameters(
    spot_price=110000,
    strike_price=105000,
    time_to_maturity=1/365,
    volatility=0.6,
    option_type=OptionType.CALL,
    is_coin_based=True  # Key for coin-settled options
)

result = bs_model.calculate_option_price(params)
print(f"Coin Price: {result.coin_based_price:.6f} BTC")
print(f"USD Equivalent: ${result.usd_price:.2f}")
print(f"Delta: {result.delta:.6f}")
```

### Portfolio Risk Analysis

```python
from crypto_bs import analyze_portfolio_risk

portfolio = [
    {
        'quantity': 10,
        'spot_price': 110000,
        'strike_price': 105000,
        'time_to_maturity': 1/365,
        'volatility': 0.6,
        'option_type': 'call',
        'underlying': 'BTC',
        'is_coin_based': True
    }
]

risk_analysis = analyze_portfolio_risk(portfolio)
print("Portfolio Delta:", risk_analysis['portfolio_summary']['total_delta'])
print("Gamma Exposure:", risk_analysis['risk_metrics']['gamma_exposure'])
```

### Real-Time Deribit Integration

```python
from crypto_bs import get_btc_forward_price, get_option_data, validate_deribit_pricing

# Get live data
F = get_btc_forward_price()
option_data = get_option_data('BTC-3SEP25-105000-C')

# Validate model against exchange
validation = validate_deribit_pricing(
    deribit_price_btc=option_data['mark_price'],
    spot=F,
    strike=105000,
    time_to_maturity=1/365,
    option_type='call'
)
print(f"Model vs Exchange difference: {validation['price_difference_btc']:.6f} BTC")
```

### Breakeven for Coin-Settled Options

For coin-settled options where the premium is paid in coin units (e.g., BTC):

```python
from crypto_bs import breakeven_price_coin_based

K = 105000
premium_btc = 0.0123  # premium in BTC

be = breakeven_price_coin_based(K, premium_btc, 'call')
print(f"Coin-based breakeven: ${be:.2f}")
```


## 📊 API Reference

### Core Functions
- `price_option(F, K, T, sigma, option_type)` - Basic Black-76 pricing
- `delta(F, K, T, sigma, option_type)` - Option delta
- `gamma(F, K, T, sigma)` - Option gamma
- `vega(F, K, T, sigma)` - Option vega
- `theta(F, K, T, sigma, option_type)` - Option theta
- `breakeven_price(K, premium, option_type)` - Breakeven calculation

### Advanced Classes
- `BlackScholesModel` - Advanced pricing with coin-based support
- `GreeksCalculator` - Portfolio-level Greeks and risk analysis
- `OptionParameters` - Structured option parameters
- `PortfolioGreeks` - Portfolio Greeks aggregation

### Data Integration
- `get_btc_forward_price()` - BTC perpetual price from Deribit
- `get_option_data(instrument)` - Option data from Deribit
- `get_available_instruments()` - List available options

## ✅ Validation Results

**Real Deribit Data Test (Sept 2025):**
- **Exchange Price**: 0.0535 BTC
- **Model Price**: 0.0542 BTC
- **Difference**: 0.0007 BTC (1.3% relative difference)
- **Implied Volatility Match**: Within market expectations

## 🎯 Use Cases

- **Crypto Options Trading**: Price and risk-manage BTC/ETH options
- **Portfolio Hedging**: Calculate Greeks for complex option portfolios
- **Risk Analysis**: Assess gamma exposure and pin risk
- **Model Validation**: Compare theoretical prices with exchange data
- **Breakeven Analysis**: Determine profitable exercise points

## 🧪 Testing

Run the test suite using pytest:

```bash
# Using pytest (recommended)
pytest tests/ -v

# Or using the test runner script
python run_tests.py

# Or run tests directly
python tests/test_pricing.py
```

All 16 tests should pass, covering:
- Basic Black-76 pricing
- Greeks calculations
- Coin-based pricing
- Advanced portfolio analysis
- Breakeven calculations

---

**Built for cryptocurrency options traders who need accurate, coin-settled pricing models.**
