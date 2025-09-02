from crypto_bs.pricing import price_option
from crypto_bs.greeks import delta, gamma, vega, theta, rho
from crypto_bs.utils import breakeven_price

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