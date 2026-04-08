import numpy as np
import pandas as pd
import pytest

from crypto_bs.historical_vol import (
    close_to_close_hv,
    parkinson_hv,
    rogers_satchell_hv,
    yang_zhang_hv,
    vol_premium,
)


def _sample_ohlc(n: int = 120) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    rng = np.random.default_rng(7)
    rets = rng.normal(0.0002, 0.02, size=n)
    close = pd.Series(100 * np.exp(np.cumsum(rets)))
    open_ = close.shift(1).fillna(close.iloc[0] * 0.995)
    spread = np.abs(rng.normal(0.01, 0.004, size=n))
    high = pd.Series(np.maximum(open_, close) * (1 + spread))
    low = pd.Series(np.minimum(open_, close) * (1 - spread))
    return open_, high, low, close


def test_close_to_close_hv_returns_positive_tail_values():
    _, _, _, close = _sample_ohlc()
    hv = close_to_close_hv(close, window=20)
    assert hv.dropna().iloc[-1] > 0


def test_parkinson_hv_returns_positive_tail_values():
    _, high, low, _ = _sample_ohlc()
    hv = parkinson_hv(high, low, window=20)
    assert hv.dropna().iloc[-1] > 0


def test_rogers_satchell_hv_returns_positive_tail_values():
    open_, high, low, close = _sample_ohlc()
    hv = rogers_satchell_hv(open_, high, low, close, window=20)
    assert hv.dropna().iloc[-1] > 0


def test_yang_zhang_hv_returns_positive_tail_values():
    open_, high, low, close = _sample_ohlc()
    hv = yang_zhang_hv(open_, high, low, close, window=20)
    assert hv.dropna().iloc[-1] > 0


def test_vol_premium_is_difference():
    iv = pd.Series([0.7, 0.8, 0.9])
    rv = pd.Series([0.4, 0.5, 0.6])
    vp = vol_premium(iv, rv)
    assert np.allclose(vp.values, np.array([0.3, 0.3, 0.3]))


def test_invalid_window_raises():
    _, _, _, close = _sample_ohlc()
    with pytest.raises(ValueError):
        close_to_close_hv(close, window=1)
