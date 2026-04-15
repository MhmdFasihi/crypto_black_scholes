import numpy as np
import pytest
from scipy.stats import norm

import crypto_bs.data_fetch as data_fetch
import crypto_bs
from crypto_bs.pricing import price_option, price_options_vectorized
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
    F, K, T, sig = 40000, 30000, 30/365, 0.8
    r_call = rho(F, K, T, sig, 'call')
    undisc_call = price_option(F, K, T, sig, 'call')
    assert r_call < 0
    assert abs(r_call + T * undisc_call / 100) < 1e-9


def test_breakeven_call():
    premium = price_option(40000, 30000, 30/365, 0.8, 'call')
    be = breakeven_price(30000, premium, 'call')
    assert be == 30000 + premium


def test_breakeven_put():
    premium = price_option(40000, 30000, 30/365, 0.8, 'put')
    be = breakeven_price(30000, premium, 'put')
    assert be == 30000 - premium


def test_T_zero_guard_scalar():
    """T=0 should not divide by zero in Black-76 helpers."""
    price_option(40000, 40000, 0.0, 0.8, 'call')


def test_put_call_parity_black76():
    F, K, T, sig = 42000.0, 40000.0, 45 / 365, 0.75
    c = price_option(F, K, T, sig, 'call')
    p = price_option(F, K, T, sig, 'put')
    assert abs((c - p) - (1.0 - K / F)) < 1e-10


def test_price_options_vectorized_matches_scalar():
    F = 40000.0
    K = np.array([30000.0, 35000.0, 40000.0])
    T = np.full(3, 30 / 365)
    sigma = np.full(3, 0.8)
    types = np.array(['call', 'put', 'call'])
    vec = price_options_vectorized(F, K, T, sigma, types)
    for i in range(3):
        assert abs(vec[i] - price_option(F, K[i], T[i], sigma[i], types[i])) < 1e-12


def test_get_btc_volatility_delegates_to_default_client(monkeypatch):
    class StubClient:
        def get_btc_volatility(self, days=90, window=30, trading_days=365):
            assert days == 90
            assert window == 30
            assert trading_days == 365
            return 0.42

    monkeypatch.setattr(data_fetch, "_get_default_client", lambda: StubClient())

    assert data_fetch.get_btc_volatility() == 0.42


def test_public_api_version_and_exports():
    assert crypto_bs.__version__ == "1.1.0"
    assert hasattr(crypto_bs, "DeribitClient")
    assert hasattr(crypto_bs, "PortfolioAnalyzer")
    assert hasattr(crypto_bs, "StrikeOutOfRangeError")


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

    assert result.coin_based_price is not None
    assert result.coin_based_price > 0

    assert result.usd_price is not None
    assert result.usd_price > 0

    assert result.delta_usd is not None
    assert result.delta_coin is not None
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
    assert 'delta_usd' in prices
    assert 'delta_coin' in prices
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

    assert 'delta_usd' in greeks
    assert 'delta_coin' in greeks
    assert 'gamma' in greeks
    assert 'theta' in greeks
    assert 'vega' in greeks
    assert 'rho' in greeks

    assert 0 < greeks['delta_usd'] < 1
    assert greeks['gamma'] > 0
    assert greeks['theta'] < 0
    assert greeks['vega'] > 0


def test_coin_based_vs_standard_pricing():
    """Test that coin-based and standard pricing give consistent USD/coin split."""
    bs_model = BlackScholesModel()

    params_standard = OptionParameters(
        spot_price=50000,
        strike_price=52000,
        time_to_maturity=30/365,
        volatility=0.8,
        risk_free_rate=0.05,
        option_type=OptionType.CALL,
        is_coin_based=False
    )

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

    assert abs(result_coin.coin_based_price - result_standard.option_price) > 1e-6

    expected_coin_price = result_standard.option_price / 50000
    assert abs(result_coin.coin_based_price - expected_coin_price) < 1e-6


def test_coin_gamma_uses_delta_usd():
    """Coin gamma must use USD delta in Γ_coin = Γ_usd/S - 2Δ_usd/S² (audit BUG-01)."""
    bs_model = BlackScholesModel()
    S, K, T_raw, vol, r, q = 50000.0, 52000.0, 30 / 365, 0.8, 0.05, 0.0
    T = max(T_raw, bs_model.min_time_to_maturity)
    params = OptionParameters(
        spot_price=S,
        strike_price=K,
        time_to_maturity=T_raw,
        volatility=vol,
        risk_free_rate=r,
        dividend_yield=q,
        option_type=OptionType.CALL,
        is_coin_based=True,
    )
    res = bs_model.calculate_option_price(params)
    d1, d2 = bs_model._calculate_d1_d2(S, K, T, r, vol, q)
    sqrt_t = np.sqrt(T)
    delta_usd = np.exp(-q * T) * norm.cdf(d1)
    gamma_usd = np.exp(-q * T) * norm.pdf(d1) / (S * vol * sqrt_t)
    expected_gamma_coin = gamma_usd / S - 2 * delta_usd / (S**2)
    assert abs(res.gamma - expected_gamma_coin) < 1e-8


def test_iv_round_trip():
    bs = BlackScholesModel()
    true_vol = 0.65
    params = OptionParameters(
        spot_price=100000,
        strike_price=105000,
        time_to_maturity=60 / 365,
        volatility=true_vol,
        risk_free_rate=0.0,
        dividend_yield=0.0,
        option_type=OptionType.CALL,
        is_coin_based=True,
    )
    px = bs.calculate_option_price(params).option_price
    params_iv = OptionParameters(
        spot_price=params.spot_price,
        strike_price=params.strike_price,
        time_to_maturity=params.time_to_maturity,
        volatility=0.5,
        risk_free_rate=params.risk_free_rate,
        dividend_yield=params.dividend_yield,
        option_type=params.option_type,
        is_coin_based=True,
    )
    iv = bs.calculate_implied_volatility(px, params_iv)
    assert abs(iv - true_vol) < 1e-5


def test_iv_rejects_below_intrinsic():
    bs = BlackScholesModel()
    params = OptionParameters(
        spot_price=50000,
        strike_price=45000,
        time_to_maturity=30 / 365,
        volatility=0.5,
        risk_free_rate=0.0,
        option_type=OptionType.CALL,
        is_coin_based=True,
    )
    intrinsic_coin = (50000 - 45000) / 50000
    with pytest.raises(ValueError, match="intrinsic"):
        bs.calculate_implied_volatility(intrinsic_coin * 0.5, params)


# --- v1.1.0 new tests ---

def test_black76_theta_identical_call_put():
    """BUG-08: Black-76 theta is mathematically identical for calls and puts (r=0 model)."""
    F, K, T, sig = 40000.0, 38000.0, 30 / 365, 0.8
    t_call = theta(F, K, T, sig, "call")
    t_put = theta(F, K, T, sig, "put")
    assert abs(t_call - t_put) < 1e-12


def test_adaptive_bump_deep_otm_no_error():
    """NEW-05: second-order Greeks computed without error for deep OTM (moneyness=0.5)."""
    greeks = calculate_option_greeks(
        spot=50000,
        strike=100000,  # moneyness = 0.5, deep OTM
        time_to_maturity=30 / 365,
        volatility=0.8,
        option_type="call",
        is_coin_based=True,
    )
    assert "gamma" in greeks
    assert greeks["gamma"] is not None


def test_adaptive_bump_high_vol_no_error():
    """NEW-05: second-order Greeks computed without error at high vol (150%)."""
    greeks = calculate_option_greeks(
        spot=50000,
        strike=52000,
        time_to_maturity=30 / 365,
        volatility=1.50,  # extreme crypto vol
        option_type="call",
        is_coin_based=False,
    )
    assert "vomma" in greeks


def test_breakeven_coin_based():
    """Breakeven for linear premium in same units as strike."""
    premium_btc = 0.01
    strike = 50000

    be_call = breakeven_price(strike, premium_btc, 'call')
    assert be_call == strike + premium_btc

    be_put = breakeven_price(strike, premium_btc, 'put')
    assert be_put == strike - premium_btc


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
