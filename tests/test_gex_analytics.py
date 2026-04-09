import numpy as np
import pandas as pd

from crypto_bs.analytics import VolatilityAnalytics
from crypto_bs.gex import compute_gex, find_gamma_flip, gex_summary


def _sample_chain() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "strike": [90000, 100000, 110000, 90000, 100000, 110000],
            "time_to_maturity": [30 / 365] * 6,
            "volatility": [0.7] * 6,
            "option_type": ["call", "call", "call", "put", "put", "put"],
            "open_interest": [1200, 1800, 900, 1400, 2000, 1300],
        }
    )


def test_compute_gex_returns_expected_columns():
    gex = compute_gex(_sample_chain(), spot=100000)
    assert list(gex.columns) == ["strike", "gex_call", "gex_put", "gex_net", "cumulative_gex"]
    assert len(gex) == 3


def test_find_gamma_flip_returns_none_or_float():
    gex = compute_gex(_sample_chain(), spot=100000)
    flip = find_gamma_flip(gex)
    assert flip is None or isinstance(flip, float)


def test_gex_summary_contains_expected_keys():
    gex = compute_gex(_sample_chain(), spot=100000)
    summary = gex_summary(gex, spot=100000)
    assert {"total_gex", "gamma_flip", "max_gex_strike", "regime", "above_flip"} <= set(summary.keys())


def test_volatility_analytics_regimes_and_signals():
    term = pd.Series(
        data=[0.85, 0.72, 0.65],
        index=[7 / 365, 30 / 365, 90 / 365],
    )
    skew = pd.Series(
        data=[0.04, 0.035, 0.03],
        index=[7 / 365, 30 / 365, 90 / 365],
    )
    hist = pd.Series(np.linspace(0.4, 0.9, 300))
    va = VolatilityAnalytics(term, skew_by_maturity=skew, historical_atm_iv=hist)
    assert va.ts_regime() == "BACKWARDATION"
    assert va.skew_regime() == "STEEP"
    assert 0 <= va.iv_percentile() <= 100
    assert isinstance(va.vol_premium(0.55), float)
    signal = va.trading_signal()
    assert "total_signal" in signal
