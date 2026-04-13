"""Interactive Plotly visualizations for volatility surfaces, smiles, GEX, and term structure.

All functions return a ``plotly.graph_objects.Figure`` — the caller is responsible
for displaying or exporting it (``fig.show()``, ``fig.write_html()``, etc.).
No side effects inside these functions.

Example::

    from crypto_bs import plot_volatility_surface, plot_smile_slice
    from crypto_bs import plot_term_structure, plot_gex

    # Build or fetch a VolatilitySurface, then:
    fig = plot_volatility_surface(surface)
    fig.show()

    fig2 = plot_smile_slice(surface)
    fig2.show()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import numpy as np
import pandas as pd

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "plotly is required for visualization. Install it with: pip install plotly"
    ) from exc

if TYPE_CHECKING:
    from .surface import VolatilitySurface
    from .analytics import VolatilityAnalytics

__all__ = [
    "plot_volatility_surface",
    "plot_smile_slice",
    "plot_term_structure",
    "plot_gex",
]

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_DEFAULT_TEMPLATE = "plotly_dark"
_CALL_COLOR = "#00b4d8"
_PUT_COLOR = "#e63946"
_NET_COLOR = "#f4a261"
_SPOT_COLOR = "#2dc653"
_FLIP_COLOR = "#e63946"


def _iv_to_pct(iv: float | np.ndarray) -> float | np.ndarray:
    """Convert IV fraction (0.80) to percentage (80.0) for axis labels."""
    return iv * 100.0


# ---------------------------------------------------------------------------
# 1. 3-D Volatility Surface
# ---------------------------------------------------------------------------


def plot_volatility_surface(
    surface: "VolatilitySurface",
    num_strikes: int = 30,
    num_maturities: Optional[int] = None,
    title: str = "Implied Volatility Surface",
    template: str = _DEFAULT_TEMPLATE,
) -> go.Figure:
    """Return an interactive 3-D implied volatility surface.

    Axes:
        - X: strike
        - Y: time to maturity (years)
        - Z: implied volatility (%)

    Args:
        surface: A fitted ``VolatilitySurface`` instance.
        num_strikes: Number of strike grid points per maturity slice.  Default 30.
        num_maturities: Number of maturity grid points.  ``None`` uses all fitted
            maturities.
        title: Plot title.
        template: Plotly template name.  Default ``"plotly_dark"``.

    Returns:
        ``go.Figure`` containing a ``Surface`` trace.
    """
    surface._require_fitted()

    fitted_maturities = np.array(sorted(surface._by_t.keys()), dtype=float)
    if num_maturities is not None and num_maturities > 0:
        maturity_grid = np.linspace(float(fitted_maturities.min()), float(fitted_maturities.max()), num_maturities)
    else:
        maturity_grid = fitted_maturities

    all_strikes = np.concatenate(
        [frame["strike"].to_numpy(dtype=float) for frame in surface._by_t.values()]
    )
    strike_grid = np.linspace(float(all_strikes.min()), float(all_strikes.max()), num_strikes)

    grid_df = surface.get_surface_grid(
        maturities=maturity_grid.tolist(),
        strike_grid=strike_grid.tolist(),
    )

    # Pivot to 2-D arrays for Surface trace
    z_matrix = []
    y_vals = sorted(grid_df["time_to_maturity"].unique())
    for t in y_vals:
        row = grid_df[grid_df["time_to_maturity"] == t].sort_values("strike")
        z_matrix.append(_iv_to_pct(row["implied_volatility"].to_numpy(dtype=float)).tolist())

    x_vals = grid_df[grid_df["time_to_maturity"] == y_vals[0]].sort_values("strike")["strike"].tolist()

    # Days-to-expiry labels for y-axis hover
    y_days = [round(t * 365, 1) for t in y_vals]

    fig = go.Figure(
        data=[
            go.Surface(
                x=x_vals,
                y=y_days,
                z=z_matrix,
                colorscale="Viridis",
                colorbar=dict(title="IV (%)"),
                hovertemplate=(
                    "Strike: %{x:,.0f}<br>"
                    "DTE: %{y:.1f}d<br>"
                    "IV: %{z:.1f}%<extra></extra>"
                ),
            )
        ]
    )
    fig.update_layout(
        title=title,
        template=template,
        scene=dict(
            xaxis_title="Strike",
            yaxis_title="Days to Expiry",
            zaxis_title="Implied Vol (%)",
            camera=dict(eye=dict(x=1.6, y=-1.6, z=0.8)),
        ),
        margin=dict(l=0, r=0, b=0, t=50),
    )
    return fig


# ---------------------------------------------------------------------------
# 2. Smile Slice
# ---------------------------------------------------------------------------


def plot_smile_slice(
    surface: "VolatilitySurface",
    maturities: Optional[list[float]] = None,
    num_points: int = 50,
    title: str = "Volatility Smile",
    template: str = _DEFAULT_TEMPLATE,
) -> go.Figure:
    """Return a 2-D smile plot with one line per maturity.

    Args:
        surface: A fitted ``VolatilitySurface`` instance.
        maturities: List of maturities (years) to plot.  ``None`` uses all fitted
            maturities.
        num_points: Number of strike points per smile curve.  Default 50.
        title: Plot title.
        template: Plotly template name.

    Returns:
        ``go.Figure`` with one ``Scatter`` trace per maturity.
    """
    surface._require_fitted()

    fitted_maturities = sorted(surface._by_t.keys())
    if maturities is None:
        plot_maturities = fitted_maturities
    else:
        plot_maturities = [float(m) for m in maturities]

    fig = go.Figure()

    colorscale = [
        f"hsl({int(i / max(len(plot_maturities) - 1, 1) * 270)}, 80%, 60%)"
        for i in range(len(plot_maturities))
    ]

    for color, t in zip(colorscale, plot_maturities):
        try:
            smile = surface.get_smile_slice(t, num_points=num_points)
        except Exception:
            continue
        dte = round(t * 365, 1)
        fig.add_trace(
            go.Scatter(
                x=smile["strike"],
                y=_iv_to_pct(smile["implied_volatility"]),
                mode="lines",
                name=f"{dte}d",
                line=dict(color=color, width=2),
                hovertemplate=(
                    f"DTE: {dte}d<br>"
                    "Strike: %{x:,.0f}<br>"
                    "IV: %{y:.2f}%<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=title,
        template=template,
        xaxis_title="Strike",
        yaxis_title="Implied Vol (%)",
        legend_title="Maturity",
        hovermode="x unified",
    )
    return fig


# ---------------------------------------------------------------------------
# 3. Term Structure
# ---------------------------------------------------------------------------


def plot_term_structure(
    surface: "VolatilitySurface",
    analytics: Optional["VolatilityAnalytics"] = None,
    title: str = "ATM Implied Volatility Term Structure",
    template: str = _DEFAULT_TEMPLATE,
) -> go.Figure:
    """Return a term-structure plot of ATM IV vs days to expiry.

    If ``analytics`` is supplied and contains ``skew_by_maturity``, a
    secondary y-axis shows the 25-delta skew alongside the ATM IV curve.

    Args:
        surface: A fitted ``VolatilitySurface`` instance.
        analytics: Optional ``VolatilityAnalytics`` for skew overlay.
        title: Plot title.
        template: Plotly template name.

    Returns:
        ``go.Figure`` with ATM IV trace and optional skew overlay.
    """
    surface._require_fitted()

    term = surface.get_term_structure()
    dte = [round(t * 365, 1) for t in term.index]
    iv_pct = _iv_to_pct(term.values.astype(float)).tolist()

    has_skew = (
        analytics is not None
        and analytics.skew_by_maturity is not None
        and not analytics.skew_by_maturity.empty
    )

    if has_skew:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()

    atm_trace = go.Scatter(
        x=dte,
        y=iv_pct,
        mode="lines+markers",
        name="ATM IV",
        line=dict(color=_CALL_COLOR, width=2),
        marker=dict(size=6),
        hovertemplate="DTE: %{x:.1f}d<br>ATM IV: %{y:.2f}%<extra></extra>",
    )

    if has_skew:
        fig.add_trace(atm_trace, secondary_y=False)
        skew_series = analytics.skew_by_maturity  # type: ignore[union-attr]
        skew_dte = [round(t * 365, 1) for t in skew_series.index]
        skew_vals = _iv_to_pct(skew_series.values.astype(float)).tolist()
        fig.add_trace(
            go.Scatter(
                x=skew_dte,
                y=skew_vals,
                mode="lines+markers",
                name="25Δ Skew (put − call)",
                line=dict(color=_NET_COLOR, width=2, dash="dash"),
                marker=dict(size=5),
                hovertemplate="DTE: %{x:.1f}d<br>Skew: %{y:.2f}%<extra></extra>",
            ),
            secondary_y=True,
        )
        fig.update_yaxes(title_text="ATM IV (%)", secondary_y=False)
        fig.update_yaxes(title_text="25Δ Skew (%)", secondary_y=True)
    else:
        fig.add_trace(atm_trace)
        fig.update_layout(yaxis_title="ATM IV (%)")

    fig.update_layout(
        title=title,
        template=template,
        xaxis_title="Days to Expiry",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.02, x=0),
    )
    return fig


# ---------------------------------------------------------------------------
# 4. GEX Bar Chart
# ---------------------------------------------------------------------------


def plot_gex(
    gex_df: pd.DataFrame,
    spot: float,
    gamma_flip: Optional[float] = None,
    title: str = "Gamma Exposure (GEX) by Strike",
    template: str = _DEFAULT_TEMPLATE,
) -> go.Figure:
    """Return an interactive GEX bar chart.

    Calls and puts are shown as separate stacked bars.  Net GEX is overlaid
    as a line.  Vertical reference lines mark the current spot price and,
    if provided, the gamma flip point.

    Args:
        gex_df: Output from ``compute_gex()`` — must have columns
            ``strike``, ``gex_call``, ``gex_put``, ``gex_net``.
        spot: Current underlying price (for reference line).
        gamma_flip: Optional gamma flip strike (linear interpolation result
            from ``find_gamma_flip()``).
        title: Plot title.
        template: Plotly template name.

    Returns:
        ``go.Figure`` with bar and line traces.
    """
    required = {"strike", "gex_call", "gex_put", "gex_net"}
    missing = required.difference(gex_df.columns)
    if missing:
        raise ValueError(f"gex_df missing required columns: {sorted(missing)}")
    if gex_df.empty:
        raise ValueError("gex_df cannot be empty")

    df = gex_df.sort_values("strike").reset_index(drop=True)
    strikes = df["strike"].tolist()
    gex_calls = df["gex_call"].tolist()
    gex_puts = df["gex_put"].tolist()
    gex_net = df["gex_net"].tolist()

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=strikes,
            y=gex_calls,
            name="Call GEX",
            marker_color=_CALL_COLOR,
            opacity=0.75,
            hovertemplate="Strike: %{x:,.0f}<br>Call GEX: %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=strikes,
            y=gex_puts,
            name="Put GEX",
            marker_color=_PUT_COLOR,
            opacity=0.75,
            hovertemplate="Strike: %{x:,.0f}<br>Put GEX: %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=strikes,
            y=gex_net,
            mode="lines",
            name="Net GEX",
            line=dict(color=_NET_COLOR, width=2),
            hovertemplate="Strike: %{x:,.0f}<br>Net GEX: %{y:,.0f}<extra></extra>",
        )
    )

    # Spot price reference line
    fig.add_vline(
        x=spot,
        line=dict(color=_SPOT_COLOR, width=2, dash="solid"),
        annotation=dict(
            text=f"Spot {spot:,.0f}",
            font=dict(color=_SPOT_COLOR),
            yref="paper",
            y=1.02,
        ),
    )

    # Gamma flip reference line
    if gamma_flip is not None:
        fig.add_vline(
            x=gamma_flip,
            line=dict(color=_FLIP_COLOR, width=2, dash="dash"),
            annotation=dict(
                text=f"Flip {gamma_flip:,.0f}",
                font=dict(color=_FLIP_COLOR),
                yref="paper",
                y=0.96,
            ),
        )

    fig.update_layout(
        title=title,
        template=template,
        barmode="relative",
        xaxis_title="Strike",
        yaxis_title="GEX (USD)",
        legend=dict(orientation="h", y=1.02, x=0),
        hovermode="x unified",
    )
    return fig
