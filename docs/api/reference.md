# API Reference

This page groups the public API by workflow rather than mirroring the package file structure.

## Pricing

- `price_option`
- `price_options_vectorized`
- `BlackScholesModel`
- `Black76Model`
- `OptionParameters`
- `OptionPricing`
- `price_coin_based_option`
- `validate_deribit_pricing`

## Greeks and risk

- `delta`
- `gamma`
- `vega`
- `theta`
- `rho`
- `GreeksCalculator`
- `calculate_option_greeks`
- `analyze_portfolio_risk`
- `PortfolioPosition`
- `PortfolioAnalyzer`
- `PortfolioDistribution`
- `PortfolioReport`
- `stress_test_portfolio`
- `build_portfolio_report`

## Market data

- `DeribitClient`
- `get_btc_forward_price`
- `get_option_data`
- `get_available_instruments`
- `get_full_chain`
- `get_iv_surface_data`
- `get_btc_price`
- `get_btc_volatility`

## Historical volatility and analytics

- `close_to_close_hv`
- `parkinson_hv`
- `rogers_satchell_hv`
- `yang_zhang_hv`
- `vol_premium`
- `VolatilityAnalytics`

`VolatilityAnalytics` exposes `term_structure_metrics()`, `skew_term_metrics()`, `summary()`, and configurable `skew_regime()` / `ts_regime()` methods with threshold override parameters (documented as BTC-specific defaults).

## GEX and surface

- `compute_gex`
- `find_gamma_flip`
- `gex_summary`
- `VolatilitySurface`

`VolatilitySurface` helpers: `get_smile_slice()`, `get_surface_grid()`, `describe_surface()`, `get_skew()`, `get_risk_reversal()`, `get_butterfly()`, `check_arbitrage()`.

`check_arbitrage()` enforces total variance monotonicity (`T × σ²` non-decreasing) as the calendar no-arbitrage condition.

## Visualization (new in v1.0)

- `plot_volatility_surface(surface, num_strikes=30, num_maturities=None, title=..., template="plotly_dark")` → `go.Figure`
- `plot_smile_slice(surface, maturities=None, num_points=50, title=..., template="plotly_dark")` → `go.Figure`
- `plot_term_structure(surface, analytics=None, title=..., template="plotly_dark")` → `go.Figure`
- `plot_gex(gex_df, spot, gamma_flip=None, title=..., template="plotly_dark")` → `go.Figure`

All visualization functions return `plotly.graph_objects.Figure`. No `.show()` is called inside the library. See the [Visualization Guide](../guides/visualization.md) for full parameter reference.

## Notes

- Time-to-maturity is expressed in years.
- Volatility inputs are decimal annualized values.
- `PortfolioPosition.risk_free_rate` defaults to `0.0` (coin-settled crypto assumption). Override explicitly if needed.
- For precise signatures and defaults, use the source docstrings in `crypto_bs/`.
