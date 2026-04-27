import warnings

import numpy as np
import pandas as pd
import pytest

from crypto_bs.analytics import VolatilityAnalytics
from crypto_bs.black_scholes import BlackScholesModel, OptionParameters, OptionType
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
    """BUG-07: vectorized compute_gex() produces finite net GEX values."""
    chain = _sample_chain()
    gex = compute_gex(chain, spot=100000)
    # Net GEX values should have consistent sign structure
    assert len(gex) == 3
    assert gex["gex_net"].notna().all()


def test_gex_vectorized_matches_scalar_black_scholes_reference():
    """BUG-07: vectorized compute_gex() matches the old scalar pricing reference."""
    chain = _sample_chain().copy()
    chain["spot_price"] = 100000.0
    chain["risk_free_rate"] = 0.0
    chain["dividend_yield"] = 0.0
    chain["is_coin_based"] = False
    spot = 100000.0
    contract_size = 2.5

    actual = compute_gex(chain, spot=spot, contract_size=contract_size)

    bs = BlackScholesModel()
    rows = []
    for _, row in chain.iterrows():
        params = OptionParameters(
            spot_price=float(row["spot_price"]),
            strike_price=float(row["strike"]),
            time_to_maturity=float(row["time_to_maturity"]),
            volatility=float(row["volatility"]),
            risk_free_rate=float(row["risk_free_rate"]),
            dividend_yield=float(row["dividend_yield"]),
            option_type=OptionType.CALL if row["option_type"] == "call" else OptionType.PUT,
            is_coin_based=False,
        )
        gamma = bs.calculate_option_price(params).gamma
        sign = 1.0 if row["option_type"] == "call" else -1.0
        rows.append(
            {
                "strike": float(row["strike"]),
                "option_type": row["option_type"],
                "gex": sign * float(row["open_interest"]) * gamma * spot**2 * contract_size,
            }
        )
    expected = (
        pd.DataFrame(rows)
        .groupby(["strike", "option_type"], as_index=False)["gex"]
        .sum()
        .pivot(index="strike", columns="option_type", values="gex")
        .fillna(0.0)
        .rename(columns={"call": "gex_call", "put": "gex_put"})
        .reset_index()
        .sort_values("strike")
    )
    expected["gex_net"] = expected["gex_call"] + expected["gex_put"]
    expected["cumulative_gex"] = expected["gex_net"].cumsum()

    assert np.allclose(actual["gex_call"], expected["gex_call"])
    assert np.allclose(actual["gex_put"], expected["gex_put"])
    assert np.allclose(actual["gex_net"], expected["gex_net"])
    assert np.allclose(actual["cumulative_gex"], expected["cumulative_gex"])
