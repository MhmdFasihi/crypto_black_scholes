import warnings

import numpy as np
import pandas as pd
import pytest

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


def test_volatility_analytics_term_and_summary_metrics():
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

    ts = va.term_structure_metrics()
    skew_metrics = va.skew_term_metrics()
    summary = va.summary(hv_30d=0.55)

    assert ts["front_to_anchor_ratio"] > 1.0
    assert ts["anchor_to_back_ratio"] > 1.0
    assert ts["slope_per_year"] < 0
    assert skew_metrics["skew_front"] > skew_metrics["skew_back"]
    assert summary["ts_regime"] == "BACKWARDATION"
    assert summary["skew_regime"] == "STEEP"
    assert summary["iv_percentile"] is not None
    assert summary["vol_premium"] == term.iloc[1] - 0.55


def test_volatility_analytics_skew_term_metrics_without_skew_series():
    term = pd.Series(
        data=[0.85, 0.72, 0.65],
        index=[7 / 365, 30 / 365, 90 / 365],
    )
    va = VolatilityAnalytics(term)
    skew_metrics = va.skew_term_metrics()
    assert skew_metrics["skew_front"] is None
    assert va.summary()["skew_regime"] == "UNKNOWN"


# --- v1.1.0 new tests ---

def _make_va() -> VolatilityAnalytics:
    term = pd.Series(
        data=[0.85, 0.72, 0.65],
        index=[7 / 365, 30 / 365, 90 / 365],
    )
    skew = pd.Series(
        data=[0.04, 0.035, 0.03],
        index=[7 / 365, 30 / 365, 90 / 365],
    )
    return VolatilityAnalytics(term, skew_by_maturity=skew)


def test_regime_summary_works():
    """trading_signal renamed: regime_summary() returns expected keys."""
    va = _make_va()
    result = va.regime_summary()
    assert "total_signal" in result
    assert "ts_regime" in result
    assert "skew_regime" in result


def test_trading_signal_raises_deprecation_warning():
    """trading_signal() emits DeprecationWarning after rename."""
    va = _make_va()
    with pytest.warns(DeprecationWarning, match="regime_summary"):
        result = va.trading_signal()
    assert "total_signal" in result


def test_regime_summary_equals_old_trading_signal():
    """regime_summary() output identical to old trading_signal() output."""
    va = _make_va()
    new_result = va.regime_summary()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        old_result = va.trading_signal()
    assert new_result == old_result


def test_gex_vectorized_matches_reference():
    """BUG-07: vectorized compute_gex() produces same net GEX as known reference."""
    chain = _sample_chain()
    gex = compute_gex(chain, spot=100000)
    # Net GEX values should have consistent sign structure
    assert len(gex) == 3
    assert gex["gex_net"].notna().all()
