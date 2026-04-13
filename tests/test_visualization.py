"""Smoke tests for crypto_bs.visualization.

Verifies that each plot function:
  - Returns a plotly.graph_objects.Figure
  - Contains at least one trace
  - Does not raise on valid input
"""

import numpy as np
import pandas as pd
import pytest

import plotly.graph_objects as go

from crypto_bs import (
    VolatilitySurface,
    plot_volatility_surface,
    plot_smile_slice,
    plot_term_structure,
    plot_gex,
)
from crypto_bs.analytics import VolatilityAnalytics
from crypto_bs.gex import compute_gex, find_gamma_flip


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SPOT = 50_000.0
MATURITIES = [7 / 365, 14 / 365, 30 / 365, 60 / 365, 90 / 365]
STRIKES = [40_000, 45_000, 47_500, 50_000, 52_500, 55_000, 60_000]


def _make_chain_df() -> pd.DataFrame:
    """Build a minimal synthetic chain with calls and puts."""
    rows = []
    for t in MATURITIES:
        for k in STRIKES:
            moneyness = k / SPOT
            atm_iv = 0.80 + 0.10 * t  # slight contango
            skew = 0.05 * (1.0 - moneyness)  # put skew
            iv = max(atm_iv + skew, 0.05)
            for opt_type in ("call", "put"):
                rows.append(
                    {
                        "strike": float(k),
                        "time_to_maturity": float(t),
                        "implied_volatility": float(iv),
                        "underlying_price": SPOT,
                        "option_type": opt_type,
                        "risk_free_rate": 0.0,
                        "dividend_yield": 0.0,
                    }
                )
    return pd.DataFrame(rows)


def _make_surface() -> VolatilitySurface:
    surf = VolatilitySurface()
    surf.fit(_make_chain_df())
    return surf


def _make_gex_df() -> pd.DataFrame:
    rows = []
    for k in STRIKES:
        for opt_type in ("call", "put"):
            rows.append(
                {
                    "strike": float(k),
                    "time_to_maturity": 30 / 365,
                    "volatility": 0.80,
                    "option_type": opt_type,
                    "open_interest": 100.0,
                }
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tests: plot_volatility_surface
# ---------------------------------------------------------------------------


def test_plot_volatility_surface_returns_figure():
    surf = _make_surface()
    fig = plot_volatility_surface(surf)
    assert isinstance(fig, go.Figure)


def test_plot_volatility_surface_has_trace():
    surf = _make_surface()
    fig = plot_volatility_surface(surf)
    assert len(fig.data) >= 1


def test_plot_volatility_surface_custom_num_strikes():
    surf = _make_surface()
    fig = plot_volatility_surface(surf, num_strikes=10)
    assert isinstance(fig, go.Figure)


def test_plot_volatility_surface_custom_title():
    surf = _make_surface()
    fig = plot_volatility_surface(surf, title="My Surface")
    assert fig.layout.title.text == "My Surface"


# ---------------------------------------------------------------------------
# Tests: plot_smile_slice
# ---------------------------------------------------------------------------


def test_plot_smile_slice_returns_figure():
    surf = _make_surface()
    fig = plot_smile_slice(surf)
    assert isinstance(fig, go.Figure)


def test_plot_smile_slice_one_trace_per_maturity():
    surf = _make_surface()
    fig = plot_smile_slice(surf)
    # Should have one Scatter trace per fitted maturity
    assert len(fig.data) == len(MATURITIES)


def test_plot_smile_slice_custom_maturities():
    surf = _make_surface()
    fig = plot_smile_slice(surf, maturities=[30 / 365, 60 / 365])
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2


def test_plot_smile_slice_custom_num_points():
    surf = _make_surface()
    fig = plot_smile_slice(surf, num_points=10)
    assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# Tests: plot_term_structure
# ---------------------------------------------------------------------------


def test_plot_term_structure_returns_figure():
    surf = _make_surface()
    fig = plot_term_structure(surf)
    assert isinstance(fig, go.Figure)


def test_plot_term_structure_has_atm_iv_trace():
    surf = _make_surface()
    fig = plot_term_structure(surf)
    trace_names = [t.name for t in fig.data]
    assert "ATM IV" in trace_names


def test_plot_term_structure_with_analytics():
    surf = _make_surface()
    analytics = VolatilityAnalytics.from_surface(surf)
    fig = plot_term_structure(surf, analytics=analytics)
    assert isinstance(fig, go.Figure)
    trace_names = [t.name for t in fig.data]
    assert "ATM IV" in trace_names
    # Skew overlay should add a second trace
    assert len(fig.data) >= 2


# ---------------------------------------------------------------------------
# Tests: plot_gex
# ---------------------------------------------------------------------------


def test_plot_gex_returns_figure():
    gex_df = compute_gex(_make_gex_df(), spot=SPOT)
    fig = plot_gex(gex_df, spot=SPOT)
    assert isinstance(fig, go.Figure)


def test_plot_gex_has_call_put_net_traces():
    gex_df = compute_gex(_make_gex_df(), spot=SPOT)
    fig = plot_gex(gex_df, spot=SPOT)
    trace_names = [t.name for t in fig.data]
    assert "Call GEX" in trace_names
    assert "Put GEX" in trace_names
    assert "Net GEX" in trace_names


def test_plot_gex_with_gamma_flip():
    gex_df = compute_gex(_make_gex_df(), spot=SPOT)
    flip = find_gamma_flip(gex_df)
    fig = plot_gex(gex_df, spot=SPOT, gamma_flip=flip)
    assert isinstance(fig, go.Figure)


def test_plot_gex_missing_column_raises():
    bad_df = pd.DataFrame({"strike": [50000], "gex_call": [100.0]})
    with pytest.raises(ValueError, match="missing required columns"):
        plot_gex(bad_df, spot=SPOT)


def test_plot_gex_empty_df_raises():
    empty = pd.DataFrame(columns=["strike", "gex_call", "gex_put", "gex_net"])
    with pytest.raises(ValueError, match="cannot be empty"):
        plot_gex(empty, spot=SPOT)


# ---------------------------------------------------------------------------
# Tests: import from top-level package
# ---------------------------------------------------------------------------


def test_visualization_importable_from_package():
    from crypto_bs import (
        plot_volatility_surface,
        plot_smile_slice,
        plot_term_structure,
        plot_gex,
    )
    assert callable(plot_volatility_surface)
    assert callable(plot_smile_slice)
    assert callable(plot_term_structure)
    assert callable(plot_gex)
