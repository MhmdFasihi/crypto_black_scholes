import pandas as pd

from crypto_bs.surface import VolatilitySurface


def _chain() -> pd.DataFrame:
    rows = []
    for t, base in [(7 / 365, 0.80), (30 / 365, 0.70), (90 / 365, 0.62)]:
        for k, off in [(90000, 0.04), (100000, 0.00), (110000, 0.03)]:
            rows.append({"strike": k, "time_to_maturity": t, "implied_volatility": base + off})
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


def test_surface_skew_and_checks():
    s = VolatilitySurface()
    s.fit(_chain())
    skew = s.get_skew(30 / 365)
    checks = s.check_arbitrage()
    assert isinstance(skew, float)
    assert "butterfly" in checks and "calendar" in checks
