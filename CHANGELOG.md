
# Changelog

All notable changes to **crypto_bs** are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-04-12

### Added

- **`crypto_bs/visualization.py`** — interactive Plotly visualization module with four public functions:
  - `plot_volatility_surface(surface)` — interactive 3-D implied volatility surface (strike × days-to-expiry × IV %).
  - `plot_smile_slice(surface, maturities)` — 2-D smile curves, one line per maturity.
  - `plot_term_structure(surface, analytics)` — ATM IV vs days-to-expiry with optional 25-delta skew overlay on a secondary axis.
  - `plot_gex(gex_df, spot, gamma_flip)` — GEX bar chart by strike with spot and gamma-flip reference lines.
  - All functions return `plotly.graph_objects.Figure`; no side effects, no `.show()` inside.
- `plotly>=5.0.0` added to package dependencies in `pyproject.toml`.
- All four visualization functions exported from `crypto_bs` top-level.
- New test file `tests/test_visualization.py` with smoke tests covering return types, trace counts, and error paths.
- `VolatilityAnalytics.skew_regime()` and `ts_regime()` now accept threshold override parameters, making regime classification configurable per asset. Default thresholds are documented as BTC-specific.
- Full quant-developer audit document at `review/CRYPTO_BS_AUDIT.md` — line-by-line formula verification of all pricing, Greeks, HV estimators, VaR/CVaR, and GEX at v0.9.0 state.

### Fixed

- **BUG-01 (MEDIUM):** VaR/CVaR simulation now uses log-normal spot returns (`exp(σ√dt·Z)`) instead of the arithmetic approximation (`1 + σ√dt·Z`). The arithmetic form materially underestimates right-tail spot levels for horizons beyond ~5 days.
- **BUG-02 (MEDIUM):** Default `spot_volatility` in `estimate_var_cvar()` is now weighted by absolute vega exposure (`|qty| × |vega|`) instead of notional (`|qty × spot_price|`). Vega-weighting more correctly captures which positions drive the simulation's volatility scale.
- **BUG-05 (LOW):** `VolatilitySurface.check_arbitrage()` calendar check now enforces total variance monotonicity (`T × σ²(T)` must be non-decreasing) instead of an absolute ATM IV jump threshold. This is the necessary condition for absence of calendar-spread arbitrage.
- **BUG-09 (INFO):** `PortfolioPosition.risk_free_rate` default changed from `0.05` to `0.0`. For coin-settled crypto options, r ≈ 0 is the correct assumption. **Breaking change** for any code relying on the old default.
- **License:** Removed AGPLv3 / commercial dual-license comment from `crypto_bs/black_scholes.py` header. All files now consistently state MIT license, matching `pyproject.toml` and `LICENSE`.

### Changed

- Package version bumped to `1.0.0`.

---

## [0.9.0] — 2026-04-12

### Added

- `VolatilitySurface.get_surface_grid(...)` for exporting a dense, plot-ready IV surface across strike and maturity.
- `VolatilitySurface.describe_surface(...)` for report-ready maturity summaries including ATM IV, skew, risk reversal, butterfly, strike coverage, and quote counts.
- `VolatilityAnalytics.term_structure_metrics(...)`, `skew_term_metrics(...)`, and `summary(...)` for explicit diagnostics beyond simple regime labels.
- New tests covering surface-grid extraction, interpolated surface descriptions, and analytics summary output.

### Changed

- README and docs now show how to export long-form surface grids and generate one-call analytics summaries from a fitted surface.
- Package version bumped to `0.9.0`.

## [0.8.0] — 2026-04-12

### Added

- Expanded `VolatilitySurface` smile analytics with:
  - `get_smile_slice(...)`
  - `get_smile_metrics(...)`
  - `get_risk_reversal(...)`
  - `get_butterfly(...)`
- `VolatilityAnalytics.from_surface(...)` for constructing analytics directly from a fitted surface.
- New tests covering delta-aware skew/risk-reversal/butterfly metrics and analytics construction from a fitted surface.

### Changed

- `VolatilitySurface.fit()` now preserves optional chain metadata such as `underlying_price`, `option_type`, `risk_free_rate`, and `dividend_yield`.
- Surface skew uses nearest-delta wing selection when metadata is available, with a strike-quantile fallback for simple strike/IV datasets.
- GitHub workflow upgraded to Node 24 compatible action majors for `actions/checkout` and `actions/setup-python`.
- Package version bumped to `0.8.0`.

### Documentation

- README and surface/analytics guides updated for smile slices, risk reversals, butterflies, and `VolatilityAnalytics.from_surface(...)`.

## [0.7.0] — 2026-04-10

### Added

- New `crypto_bs.portfolio` module with:
  - `PortfolioPosition`
  - `PortfolioAnalyzer`
  - `PortfolioDistribution`
  - `PortfolioReport`
  - `stress_test_portfolio(...)`
  - `build_portfolio_report(...)`
- New portfolio analytics capabilities:
  - position-level breakdowns
  - concentration summaries by underlying and expiry bucket
  - full-repricing stress tests over spot, volatility, and forward time
  - scenario-based VaR / CVaR estimation using portfolio Greeks
- New tests in `tests/test_portfolio.py` covering report shape, stress behavior, and tail-risk outputs.

### Changed

- Existing portfolio risk calculations now carry `risk_free_rate` and `dividend_yield` through internal repricing paths more consistently.
- GitHub publish workflow now skips TestPyPI publication when `TEST_PYPI_API_TOKEN` is absent instead of failing the whole `main` push workflow.
- PyPI/TestPyPI publish steps now use `skip-existing: true` so release reruns are idempotent.
- Package version bumped to `0.7.0`.

### Documentation

- README updated with portfolio report examples and API summary for the new module.
- Docs now include a dedicated portfolio risk guide and target `v0.7.0`.

## [0.6.0] — 2026-04-10

### Added

- New `crypto_bs.data_fetch.DeribitClient` with retry-enabled HTTP handling, short-lived response caching, and lightweight public-API pacing.
- New top-level market-data helpers:
  - `get_full_chain(currency="BTC", min_open_interest=0)`
  - `get_iv_surface_data(currency="BTC", min_open_interest=0)`
- New test file `tests/test_data_fetch.py` covering ticker normalization, full-chain construction, surface-input filtering, and realized-volatility behavior.
- New local documentation tree under `docs/` with guides, cookbook recipes, and grouped API reference pages.

### Changed

- `get_btc_volatility()` now computes realized BTC volatility from CoinGecko daily closes using the existing `close_to_close_hv` estimator instead of raising `NotImplementedError`.
- Existing market-data wrappers now delegate through a shared client implementation for consistent timeout, retry, and caching behavior.
- Public API exports now include `DeribitClient`, `get_full_chain`, and `get_iv_surface_data`.
- Package version bumped to `0.6.0`.

### Documentation

- README updated for the new market-data client, docs index, and realized-volatility workflow.
- `docs/README.md` now resolves to actual guide and reference pages instead of placeholder links.

## [0.5.0] — 2026-04-09

### Added

- New `crypto_bs.surface` module with `VolatilitySurface`:
  - `fit(chain_df)`
  - `get_iv(strike, time_to_maturity)`
  - `get_atm_iv(time_to_maturity)`
  - `get_term_structure()`
  - `get_skew(time_to_maturity, delta=0.25)`
  - `check_arbitrage()`
- New tests in `tests/test_surface.py` for fit/interpolation/term-structure/skew/arbitrage checks.

### Changed

- Package version bumped to `0.5.0`.
- Public API exports now include `VolatilitySurface`.
- Release date aligned to 2026-04-09.

## [0.4.0] — 2026-04-06

### Added

- New `crypto_bs.gex` module:
  - `compute_gex(chain_df, spot, ...)`
  - `find_gamma_flip(gex_df)`
  - `gex_summary(gex_df, spot)`
- New `crypto_bs.analytics` module with `VolatilityAnalytics`:
  - `iv_percentile()`
  - `vol_premium(hv_30d)`
  - `skew_regime()`
  - `ts_regime()`
  - `trading_signal()`
- New tests in `tests/test_gex_analytics.py` for GEX outputs, gamma flip behavior, and analytics regimes/signals.

### Changed

- Package version bumped to `0.4.0`.
- Public API exports now include GEX and analytics helpers directly from `crypto_bs`.
- README updated for GEX and analytics examples.

## [0.3.0] — 2026-04-06

### Added

- New `crypto_bs.historical_vol` module with realized-vol estimators:
  - `close_to_close_hv`
  - `parkinson_hv`
  - `rogers_satchell_hv`
  - `yang_zhang_hv`
  - `vol_premium`
- Input validation for estimator window and positive OHLC inputs.
- New test file `tests/test_historical_vol.py` covering estimator outputs and edge-case validation.

### Changed

- Package version bumped to `0.3.0`.
- Public API exports now include historical-vol functions directly from `crypto_bs`.
- README updated to document the new historical volatility functionality.

### Notes

- This release implements the historical-volatility part of the roadmap from the audit.
- Vol-surface fitting remains planned for a subsequent release.

## [0.2.0] — 2026-04-05

### Fixed

- **Coin-based gamma** — Uses the correct cross term: Γ_coin = Γ_usd/S − 2·Δ_usd/S² (previously mixed in coin delta and understated the adjustment).
- **`greeks.rho`** — Computes rate sensitivity from the **coin-denominated** Black-76 premium (aligned with `price_option`), with optional `risk_free_rate`; no longer a hardcoded zero.
- **Implied volatility** — Default upper search bound raised to **20.0** (2000% annualized vol) for extreme crypto regimes; rejects non-positive market price and prices **below intrinsic** with a clear `ValueError`.

### Changed (breaking)

- **`OptionPricing`** — Replaced single `delta` with **`delta_usd`** (∂V_usd/∂S, use for hedging) and **`delta_coin`** (∂(V_usd/S)/∂S, sensitivity of coin premium to spot). Update code that read `result.delta`.
- **`price_coin_based_option` / `validate_deribit_pricing`** — Return dict keys `delta_usd` and `delta_coin` instead of `delta`.
- **`GreeksProfile`** — Fields **`delta_usd`** and **`delta_coin`**; `to_dict()` also includes **`delta`** as an alias of `delta_usd` for convenience. Portfolio aggregation uses **USD delta** for `total_delta` and related totals.
- **`get_btc_volatility()`** — Removed the fake constant `0.5`; the function now **`NotImplementedError`** with guidance until a historical-vol helper exists.

### Added

- **`price_options_vectorized`** — NumPy vectorized Black-76 coin premiums over strikes / maturities / vols in one call.
- **Guards** — `T` and `sigma` validated in `pricing` / `greeks` modules; very small `T` floored (1 hour in years) to avoid division by zero. `BlackScholesModel` default minimum `T` is **1/8760** (one hour).
- **HTTP clients** — Deribit and CoinGecko `requests` calls use **`timeout=10`** and `raise_for_status()` where applicable.
- **Tests** — Put–call parity, vectorized vs scalar parity, IV round-trip and intrinsic check, coin-gamma identity, `T=0` guard, `get_btc_volatility` behavior.

### Documentation

- README updated for 0.2.0 API, testing with conda, and link to this file.

## [0.1.0] — earlier

- Initial public API: Black-76 and Black-Scholes with coin-settled adjustments, basic and portfolio Greeks, Deribit helpers, IV via Brent’s method, breakeven utilities.

[0.9.0]: https://github.com/MhmdFasihi/crypto_black_scholes/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/MhmdFasihi/crypto_black_scholes/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/MhmdFasihi/crypto_black_scholes/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/MhmdFasihi/crypto_black_scholes/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/MhmdFasihi/crypto_black_scholes/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/MhmdFasihi/crypto_black_scholes/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/MhmdFasihi/crypto_black_scholes/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/MhmdFasihi/crypto_black_scholes/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/MhmdFasihi/crypto_black_scholes/releases/tag/v0.1.0
