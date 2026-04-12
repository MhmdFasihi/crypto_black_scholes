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

## GEX and surface

- `compute_gex`
- `find_gamma_flip`
- `gex_summary`
- `VolatilitySurface`

`VolatilitySurface` now includes smile-specific helpers such as `get_smile_slice()`, `get_surface_grid()`, `describe_surface()`, `get_skew()`, `get_risk_reversal()`, and `get_butterfly()`.

`VolatilityAnalytics` also exposes richer summary helpers including `term_structure_metrics()`, `skew_term_metrics()`, and `summary()`.

## Notes

- Time-to-maturity is expressed in years.
- Volatility inputs are decimal annualized values.
- For precise signatures and defaults, use the source docstrings in `crypto_bs/`.
