import pandas as pd

from crypto_bs.analytics import VolatilityAnalytics
from crypto_bs.surface import VolatilitySurface


def _chain() -> pd.DataFrame:
    rows = []
    strikes = [85000, 90000, 95000, 100000, 105000, 110000, 115000]
    offsets = {
        85000: 0.11,
        90000: 0.07,
        95000: 0.03,
        100000: 0.00,
        105000: 0.01,
        110000: 0.02,
        115000: 0.03,
    }
    for t, base in [(7 / 365, 0.80), (30 / 365, 0.70), (90 / 365, 0.62)]:
        for strike in strikes:
            iv = base + offsets[strike]
            for option_type in ("call", "put"):
                rows.append(
                    {
                        "strike": strike,
                        "time_to_maturity": t,
                        "implied_volatility": iv,
                        "underlying_price": 100000.0,
                        "option_type": option_type,
                    }
                )
    return pd.DataFrame(rows)


def test_surface_fit_and_get_iv():
    s = VolatilitySurface()
    s.fit(_chain())
    iv = s.get_iv(100000, 30 / 365)
    assert iv > 0


def test_surface_get_atm_iv_and_term_structure():
    s = VolatilitySurface()
    s.fit(_chain())
    atm = s.get_atm_iv(30 / 365)
    ts = s.get_term_structure()
    assert atm > 0
    assert len(ts) == 3


def test_surface_smile_slice_and_metrics():
    s = VolatilitySurface()
    s.fit(_chain())
    smile = s.get_smile_slice(30 / 365, num_points=9)
    skew = s.get_skew(30 / 365)
    rr = s.get_risk_reversal(30 / 365)
    bf = s.get_butterfly(30 / 365)
    checks = s.check_arbitrage()
    assert len(smile) == 9
    assert {"strike", "implied_volatility", "moneyness", "log_moneyness"} <= set(smile.columns)
    assert isinstance(skew, float)
    assert skew > 0
    assert rr < 0
    assert abs(rr + skew) < 1e-10
    assert bf >= 0
    assert "butterfly" in checks and "calendar" in checks


def test_surface_metrics_fallback_without_option_metadata():
    s = VolatilitySurface()
    s.fit(_chain()[["strike", "time_to_maturity", "implied_volatility"]])
    skew = s.get_skew(30 / 365)
    rr = s.get_risk_reversal(30 / 365)
    assert skew > 0
    assert rr < 0


def test_volatility_analytics_from_surface():
    s = VolatilitySurface()
    s.fit(_chain())
    analytics = VolatilityAnalytics.from_surface(s)
    assert analytics.ts_regime() == "BACKWARDATION"
    assert analytics.skew_regime() == "STEEP"
