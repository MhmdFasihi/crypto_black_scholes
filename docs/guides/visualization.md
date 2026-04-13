# Visualization Guide

`crypto_bs` ships four interactive Plotly functions, all new in **v1.0.0**. Every function returns a `plotly.graph_objects.Figure` with no side effects — `.show()` is never called inside the library.

## Prerequisites

`plotly>=5.0.0` is a package dependency, so it is installed automatically with `pip install crypto-bs`. If you manage the environment manually:

```bash
pip install "plotly>=5.0.0"
```

## `plot_volatility_surface`

Renders an interactive 3-D implied-volatility surface (strike × days-to-expiry × IV %).

```python
from crypto_bs import VolatilitySurface, plot_volatility_surface

surface = VolatilitySurface()
surface.fit(chain_df)

fig = plot_volatility_surface(surface)
fig.show()
```

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `surface` | `VolatilitySurface` | — | A fitted surface object |
| `num_strikes` | `int` | `30` | Number of strike grid points per maturity slice |
| `num_maturities` | `int \| None` | `None` | Maturity grid points (defaults to all fitted maturities) |
| `title` | `str` | `"Implied Volatility Surface"` | Plot title |
| `template` | `str` | `"plotly_dark"` | Plotly template name |

**Returns** `plotly.graph_objects.Figure` with one `go.Surface` trace.

## `plot_smile_slice`

Plots 2-D smile curves, one line per maturity, across the fitted strike range.

```python
from crypto_bs import plot_smile_slice

fig = plot_smile_slice(surface)
fig.show()

# Subset of maturities
fig = plot_smile_slice(surface, maturities=[30/365, 60/365])
fig.show()
```

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `surface` | `VolatilitySurface` | — | A fitted surface object |
| `maturities` | `list[float] \| None` | `None` | Maturities to plot in years (defaults to all fitted) |
| `num_points` | `int` | `50` | Strike grid points per smile |
| `title` | `str` | `"Volatility Smile"` | Plot title |
| `template` | `str` | `"plotly_dark"` | Plotly template name |

**Returns** `go.Figure` with one `go.Scatter` trace per maturity (HSL color cycling).

## `plot_term_structure`

Plots ATM IV versus days-to-expiry. When `analytics` is provided and contains skew data, a 25-delta skew overlay is added on a secondary y-axis.

```python
from crypto_bs import VolatilityAnalytics, plot_term_structure

analytics = VolatilityAnalytics.from_surface(surface)

# ATM IV only
fig = plot_term_structure(surface)
fig.show()

# With skew overlay
fig = plot_term_structure(surface, analytics=analytics)
fig.show()
```

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `surface` | `VolatilitySurface` | — | A fitted surface object |
| `analytics` | `VolatilityAnalytics \| None` | `None` | Optional analytics for skew overlay |
| `title` | `str` | `"ATM Implied Volatility Term Structure"` | Plot title |
| `template` | `str` | `"plotly_dark"` | Plotly template name |

**Returns** `go.Figure`. Uses `make_subplots(secondary_y=True)` only when skew overlay data is present.

## `plot_gex`

GEX bar chart by strike: call GEX (positive), put GEX (negative), and a net GEX scatter line. Vertical reference lines mark spot and optionally the gamma-flip level.

```python
from crypto_bs import compute_gex, find_gamma_flip, plot_gex

gex_df = compute_gex(chain_df, spot=100000)
flip = find_gamma_flip(gex_df)

fig = plot_gex(gex_df, spot=100000, gamma_flip=flip)
fig.show()
```

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `gex_df` | `pd.DataFrame` | — | Output of `compute_gex()` — must contain `strike`, `gex_call`, `gex_put`, `gex_net` |
| `spot` | `float` | — | Current spot price (vertical reference line) |
| `gamma_flip` | `float \| None` | `None` | Gamma-flip level from `find_gamma_flip()` |
| `title` | `str` | `"Gamma Exposure (GEX) by Strike"` | Plot title |
| `template` | `str` | `"plotly_dark"` | Plotly template name |

**Returns** `go.Figure` with `go.Bar` traces for call/put GEX and a `go.Scatter` trace for net GEX.

**Raises** `ValueError` if `gex_df` is missing required columns or is empty.

## Common patterns

### Export to HTML

```python
fig = plot_volatility_surface(surface)
fig.write_html("iv_surface.html")
```

### Light theme

```python
fig = plot_smile_slice(surface, template="plotly_white")
fig.show()
```

### Embed in Jupyter

All four functions return standard Plotly figures — they render inline in Jupyter notebooks automatically when `plotly` is installed.

```python
from crypto_bs import plot_volatility_surface
fig = plot_volatility_surface(surface)
fig  # displays inline
```

### Save as PNG/SVG (requires kaleido)

```bash
pip install kaleido
```

```python
fig.write_image("surface.png")
fig.write_image("surface.svg")
```
