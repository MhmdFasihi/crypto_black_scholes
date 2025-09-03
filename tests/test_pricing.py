from crypto_bs.pricing import price_option
from crypto_bs.greeks import delta, gamma, vega, theta, rho
from crypto_bs.utils import breakeven_price

# Import advanced classes
from crypto_bs.black_scholes import BlackScholesModel, OptionParameters, OptionType, price_coin_based_option
from crypto_bs.greeks_calculator import calculate_option_greeks

def test_call_price_positive():
    price = price_option(40000, 30000, 30/365, 0.8, 'call')
    assert price > 0

def test_put_price_positive():
    price = price_option(40000, 30000, 30/365, 0.8, 'put')
    assert price > 0

def test_call_delta():
    d = delta(40000, 30000, 30/365, 0.8, 'call')
    assert 0 < d < 1

def test_put_delta():
    d = delta(40000, 30000, 30/365, 0.8, 'put')
    assert -1 < d < 0

def test_gamma():
    g = gamma(40000, 30000, 30/365, 0.8)
    assert g > 0

def test_vega():
    v = vega(40000, 30000, 30/365, 0.8)
    assert v > 0

def test_theta_call():
    t = theta(40000, 30000, 30/365, 0.8, 'call')
    assert t < 0

def test_theta_put():
    t = theta(40000, 30000, 30/365, 0.8, 'put')
    assert t < 0

def test_rho():
    r = rho(40000, 30000, 30/365, 0.8, 'call')
    assert r == 0

def test_breakeven_call():
    premium = price_option(40000, 30000, 30/365, 0.8, 'call')
    be = breakeven_price(30000, premium, 'call')
    assert be == 30000 + premium

def test_breakeven_put():
    premium = price_option(40000, 30000, 30/365, 0.8, 'put')
    be = breakeven_price(30000, premium, 'put')
    assert be == 30000 - premium

# Advanced tests for coin-based options
def test_coin_based_pricing():
    """Test advanced Black-Scholes with coin-based pricing."""
    bs_model = BlackScholesModel()

    params = OptionParameters(
        spot_price=50000,
        strike_price=52000,
        time_to_maturity=30/365,
        volatility=0.8,
        risk_free_rate=0.05,
        option_type=OptionType.CALL,
        is_coin_based=True
    )

    result = bs_model.calculate_option_price(params)

    # Check that coin-based price is returned
    assert result.coin_based_price is not None
    assert result.coin_based_price > 0

    # Check that USD price is also calculated
    assert result.usd_price is not None
    assert result.usd_price > 0

    # Check Greeks are calculated
    assert result.delta is not None
    assert result.gamma is not None
    assert result.theta is not None
    assert result.vega is not None

def test_quick_coin_based_pricing():
    """Test the quick coin-based pricing function."""
    prices = price_coin_based_option(
        spot=50000,
        strike=52000,
        time_to_maturity=30/365,
        volatility=0.8,
        option_type='call',
        risk_free_rate=0.05
    )

    assert 'coin_price' in prices
    assert 'usd_price' in prices
    assert 'delta' in prices
    assert 'gamma' in prices
    assert 'theta' in prices
    assert 'vega' in prices
    assert 'rho' in prices

    assert prices['coin_price'] > 0
    assert prices['usd_price'] > 0

def test_advanced_greeks_calculator():
    """Test the advanced Greeks calculator."""
    greeks = calculate_option_greeks(
        spot=50000,
        strike=52000,
        time_to_maturity=30/365,
        volatility=0.8,
        option_type='call',
        is_coin_based=True
    )

    # Check that all basic Greeks are present
    assert 'delta' in greeks
    assert 'gamma' in greeks
    assert 'theta' in greeks
    assert 'vega' in greeks
    assert 'rho' in greeks

    # Check values are reasonable
    assert greeks['delta'] > 0 and greeks['delta'] < 1
    assert greeks['gamma'] > 0
    assert greeks['theta'] < 0  # Theta is negative for long positions
    assert greeks['vega'] > 0

def test_coin_based_vs_standard_pricing():
    """Test that coin-based and standard pricing give different results."""
    bs_model = BlackScholesModel()

    # Standard pricing
    params_standard = OptionParameters(
        spot_price=50000,
        strike_price=52000,
        time_to_maturity=30/365,
        volatility=0.8,
        risk_free_rate=0.05,
        option_type=OptionType.CALL,
        is_coin_based=False
    )

    # Coin-based pricing
    params_coin = OptionParameters(
        spot_price=50000,
        strike_price=52000,
        time_to_maturity=30/365,
        volatility=0.8,
        risk_free_rate=0.05,
        option_type=OptionType.CALL,
        is_coin_based=True
    )

    result_standard = bs_model.calculate_option_price(params_standard)
    result_coin = bs_model.calculate_option_price(params_coin)

    # Coin-based price should be different from standard price
    assert abs(result_coin.coin_based_price - result_standard.option_price) > 1e-6

    # But they should be related (coin price = standard price / spot)
    expected_coin_price = result_standard.option_price / 50000
    assert abs(result_coin.coin_based_price - expected_coin_price) < 1e-6

def test_breakeven_coin_based():
    """Test breakeven calculation for coin-based options."""
    # For coin-based options, premium is in BTC, breakeven is in USD
    premium_btc = 0.01  # 0.01 BTC premium
    strike = 50000  # $50,000 strike

    # Call option breakeven
    be_call = breakeven_price(strike, premium_btc, 'call')
    assert be_call == strike + premium_btc

    # Put option breakeven
    be_put = breakeven_price(strike, premium_btc, 'put')
    assert be_put == strike - premium_btc