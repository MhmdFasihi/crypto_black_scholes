# Project State: `crypto_bs` at `v0.9.0`

Date: 2026-04-12

Audience: senior quantitative developer / quantitative engineering lead

## Executive Summary

`crypto_bs` is no longer in the state described by the original audit. The current repository at `v0.9.0` is a working Python toolkit for European coin-settled crypto options with:

- corrected pricing and Greek semantics for coin-denominated contracts
- vectorized Black-76 chain pricing
- historical volatility estimators
- GEX analytics
- a lightweight implied-volatility surface layer
- smile, skew, risk-reversal, butterfly, and term-structure diagnostics
- a reusable Deribit market-data client with retry/cache/pacing
- portfolio reporting, deterministic stress testing, and scenario-based VaR/CVaR
- a functioning GitHub release workflow with PyPI publication

In practical terms, the project is already beyond the audit's planned `0.4.0` scope and includes part of the audit's planned `1.0.0` scope. The main remaining delta to the audit's `1.0.0` target is not "basic functionality"; it is production polish and architecture:

- no streaming / WebSocket layer
- no strategy recommendation engine
- no parametrized arbitrage-aware surface model such as SVI/SABR
- no explicit 95%+ coverage / benchmark-validation bar
- no fully productized trading guide / operational guide

Current status should be described as:

- mathematically usable for European crypto options workflows
- materially more complete than the audit roadmap up to `0.4.0`
- not yet at the audit's envisioned `1.0.0` production platform

## Current Release / Validation State

- Package version: `0.9.0`
- Packaging metadata: `pyproject.toml` declares `requires-python >=3.10`
- GitHub release / PyPI publication path is operational
- Local regression status on 2026-04-12: `50 passed, 1 warning`
- CI publish workflow exists and performs:
  - test on push to `main`
  - optional TestPyPI publication on `main`
  - PyPI publication on GitHub release

Operationally, release engineering is no longer a future item. It is already part of the current repo state.

## What Has Actually Been Delivered Since The Audit

The audit's version plan is no longer the right mental model for this repository. The actual project evolved like this:

| Actual release | Delivered scope | Relation to audit |
|---|---|---|
| `0.2.0` | corrected coin-Greek semantics, split `delta_usd` / `delta_coin`, real `rho`, IV bounds/intrinsic checks, `T` guards, vectorized Black-76 pricing, request timeouts | covers the audit's bug-fix release almost exactly |
| `0.3.0` | realized-volatility estimators (`close_to_close`, Parkinson, Rogers-Satchell, Yang-Zhang) | covers the audit's HV module |
| `0.4.0` | GEX analytics and first volatility-regime analytics layer | covers the audit's GEX + analytics milestone |
| `0.5.0` | first `VolatilitySurface` foundation | surface work split out later than the audit assumed |
| `0.6.0` | `DeribitClient`, normalized chain/surface fetchers, docs tree, CoinGecko-based realized BTC vol | partially covers the audit's data-layer ambitions |
| `0.7.0` | portfolio report layer, concentration, stress, VaR/CVaR | this is already part of audit `1.0.0` scope |
| `0.8.0` | richer smile analytics, delta-aware skew / RR / BF, analytics from fitted surface | extends surface analytics beyond the audit's early milestones |
| `0.9.0` | dense surface-grid export, per-maturity surface summaries, richer term/skew metrics summaries | not explicitly in the audit, but useful for quant workflows and reporting |

Net: the repo did not follow the audit's proposed release numbering after `0.4.0`; it decomposed the next features into more granular deliverables.

## Capability Inventory At `v0.9.0`

### 1. Pricing Core

Implemented:

- module-level Black-76 helpers for forward-based coin premium
- class-based `BlackScholesModel` for spot-based pricing
- explicit support for coin-based premiums
- `delta_usd` and `delta_coin` separated in the result model
- corrected coin-gamma cross term
- IV solving with intrinsic-value guard and widened search bounds
- vectorized Black-76 pricing via `price_options_vectorized`

Quant significance:

- the project no longer has the audit's original hedge-delta ambiguity
- `delta_usd` is the hedge delta; `delta_coin` is explicitly just premium sensitivity
- the core valuation layer is suitable for European vanilla crypto options under Black/Black-Scholes assumptions

### 2. Historical Volatility

Implemented:

- close-to-close HV
- Parkinson HV
- Rogers-Satchell HV
- Yang-Zhang HV
- simple IV-vs-RV premium helper
- realized BTC volatility fetched from CoinGecko daily history

Quant significance:

- the repo now has a usable realized-vol baseline for comparing listed IV to realized risk
- this closes one of the audit's large early analytical gaps

### 3. GEX Layer

Implemented:

- strike-level GEX from OI and model gamma
- cumulative GEX
- gamma-flip estimation
- regime summary

Design note:

- current GEX uses a simple sign convention parameter (`short_gamma` / `long_gamma`)
- contract-size handling exists as a scalar input, not as exchange-specific metadata abstraction

Quant significance:

- enough to support strike-level dealer-position diagnostics
- still a lightweight abstraction rather than a venue-calibrated risk engine

### 4. Volatility Surface Layer

Implemented:

- fit from quote table with `strike`, `time_to_maturity`, `implied_volatility`
- preservation of optional metadata:
  - `underlying_price`
  - `option_type`
  - `risk_free_rate`
  - `dividend_yield`
- strike interpolation within maturity buckets
- linear interpolation across maturities
- ATM IV extraction and term structure
- smile slices
- delta-aware smile metrics when metadata is available:
  - skew
  - risk reversal
  - butterfly
- fallback strike-quantile wing metrics when metadata is absent
- `get_surface_grid(...)` for dense export
- `describe_surface(...)` for report-ready maturity summaries
- heuristic calendar / butterfly consistency checks

Quant significance:

- the surface layer is now useful for exploratory analysis, downstream reporting, and dashboarding
- the smile metrics are not just strike-proxy metrics when quote metadata exists; they can be derived from nearest-delta wing selection using repricing

Important design choice:

- this is still a lightweight empirical interpolation surface
- it is not SVI, SABR, or any arbitrage-free parametrized calibration framework

### 5. Volatility Analytics Layer

Implemented:

- `iv_percentile()` on provided ATM-IV history
- `vol_premium(hv_30d)`
- `skew_regime()`
- `ts_regime()`
- `trading_signal()`
- `from_surface(...)`
- `term_structure_metrics(...)`
- `skew_term_metrics(...)`
- `summary(...)`

Quant significance:

- analytics are no longer only regime labels
- current APIs provide report-ready explicit diagnostics:
  - front/anchor/back ratios
  - slope estimates
  - curvature
  - skew term movement
  - optional IV percentile and IV-vs-RV premium

Constraint:

- historical IVP is only as good as the user-supplied historical ATM-IV series
- the repo does not yet own a historical surface storage/replay layer

### 6. Market-Data Layer

Implemented:

- synchronous `DeribitClient`
- retry-enabled HTTP session
- short-lived in-memory cache
- lightweight pacing against public API limits
- normalized helpers for:
  - available instruments
  - ticker data
  - BTC forward proxy
  - full chain
  - IV surface input
  - BTC spot price
  - BTC realized volatility history

Quant significance:

- enough for periodic chain pulls, research notebooks, and release examples
- not yet a high-throughput or real-time ingestion architecture

Important design choice:

- the client is `requests`-based and synchronous
- the audit had envisioned an async `aiohttp` client with explicit batch / streaming orientation

### 7. Portfolio / Risk Layer

Implemented:

- `PortfolioPosition`
- `PortfolioAnalyzer`
- position-level breakdown with Greeks and values
- concentration summary by underlying and expiry bucket
- deterministic scenario stress testing over:
  - spot shocks
  - volatility shocks
  - days-forward decay
- scenario-based VaR / CVaR by full repricing
- combined `PortfolioReport`

Quant significance:

- this is already part of what the audit described as a `1.0.0` feature set
- VaR/CVaR is based on full repricing, not only first-order Greek approximation

Current modeling detail:

- spot and vol shocks are sampled from correlated Gaussian drivers
- shock scale is driven by a single spot-volatility input or weighted average default
- this is a practical portfolio monitor, not a historical simulation or pathwise derivatives risk engine

### 8. Documentation / Release Engineering

Implemented:

- local docs tree under `docs/`
- release notes in `CHANGELOG.md`
- GitHub Actions workflow for test and publish
- PyPI release path via GitHub release

Quant significance:

- the project is already consumable as a package and not just a local code artifact
- release / distribution was originally deferred in the audit to `1.0.0`; it is already delivered

## Current Quantitative / Architectural Positioning

The best way to think about the current repo is:

- strong enough for research, prototyping, and small production-style utilities around European crypto options
- not yet a fully productionized volatility platform

It is strongest in:

- vanilla pricing correctness
- explicit Greek semantics for coin-settled options
- practical chain analytics
- portfolio inspection and scenario repricing
- lightweight distribution and docs

It is weakest in:

- live market-state management
- model-based surface calibration
- full production observability / persistence / contract abstraction
- prescriptive strategy logic

## Important Deviations From The Audit's Implied Architecture

### Surface: interpolation instead of calibration

The audit assumed the surface would move toward SVI quickly. That did not happen. The current surface:

- interpolates observed implied volatilities
- preserves optional metadata
- computes useful diagnostics

What it does not do:

- fit a parametric smile
- enforce no-arbitrage conditions globally
- produce a calibration object with fit errors / stability measures

This is a reasonable pragmatic choice for a research library, but it is materially different from the audit's implied target architecture.

### Data client: sync and simple instead of async and streaming-capable

The audit envisioned:

- async I/O
- stronger batch semantics
- eventual live updates

The current implementation chose:

- synchronous `requests`
- retries
- cache
- pacing

That is enough for notebook/research and periodic refresh. It is not the right architecture for live intraday surface maintenance.

### Analytics: descriptive first, prescriptive later

Current analytics tell you:

- what the term structure looks like
- how skew behaves
- whether the regime is steep / inverted / backwardated
- what the current IV-vs-RV spread is

They do not yet tell you:

- what trade structure to put on
- what hedge package to run
- what expected PnL / carry / convexity tradeoff applies by structure

## Current Known Gaps / Risks

These are the highest-signal gaps in the current repository state.

### 1. No streaming or real-time IV update architecture

There is no:

- WebSocket client
- incremental order-book / quote update handling
- stateful live surface refresh loop
- surface history persistence

Impact:

- unsuitable for live monitoring, intraday hedging, or event-driven signal generation

### 2. Surface is analytically useful but not calibration-grade

There is no:

- SVI calibration
- SABR calibration
- fit diagnostics
- stable surface parameter state
- visualization helper promised in the audit examples

Impact:

- current surface is adequate for interpolation and diagnostics
- it is not yet strong enough for arbitrage-aware model calibration or advanced smile trading research

### 3. Portfolio risk is scenario-based but still simplified

Limitations:

- Gaussian shock model
- no historical simulation
- no jump process
- no liquidity / slippage / execution model
- no exchange contract metadata abstraction beyond simple scalar inputs

Impact:

- good for ranking / monitoring / sensitivity analysis
- not yet a desk-grade risk engine

### 4. Analytics history layer is user-supplied, not system-owned

`iv_percentile()` depends on a provided historical ATM-IV series. The package does not yet maintain:

- historical surfaces
- rolling regime state
- persistent local market-data store

Impact:

- analytics can be used if upstream history exists
- the library does not yet own that state-management problem

### 5. Coverage / validation posture is still informal

Current regression state is good, but the repo does not yet publish:

- coverage percentage
- golden benchmark datasets
- cross-library numerical validation report
- calibration stability / convergence tests
- live integration test suite

Impact:

- reliability is much better than the original audit state
- it is not yet presented with the evidence base expected of a mature quant platform

### 6. License metadata is inconsistent

Observed mismatch:

- repository `LICENSE` is MIT
- `pyproject.toml` declares MIT
- `crypto_bs/black_scholes.py` header still says AGPLv3 or commercial

Impact:

- this is a legal / packaging ambiguity
- it should be resolved before any `1.0.0` positioning

### 7. Runtime / support metadata is inconsistent

Observed mismatch:

- package metadata declares `requires-python >= 3.10`
- local development / validation was run from a Python 3.9 virtual environment
- CI publish workflow tests on Python 3.11

Impact:

- support matrix and developer environment are not fully aligned
- this is not blocking research use, but it is avoidable release ambiguity

## Gap Analysis: `v0.9.0` vs The Audit's `v1.0.0`

This is the key question if the audit's roadmap is still being used as a target.

### Items From Audit `v1.0.0` That Are Already Delivered Early

The audit's `1.0.0` plan included:

- `crypto_bs/portfolio.py`
- full portfolio risk report
- PyPI publishing

Those are already in the repo today:

- portfolio module shipped in actual `0.7.0`
- GitHub release + PyPI publish path is live before `1.0.0`
- docs are materially better than the audit's starting point

So the gap to audit `1.0.0` is not "build portfolio risk" or "get onto PyPI". Those are done.

### Gap 1: No `streaming.py` / real-time surface infrastructure

Audit `1.0.0` expected:

- live IV updates via WebSocket
- a real-time IV surface

Current `0.9.0` has none of that.

Why this matters for a senior quant developer:

- without a streaming state machine, the library cannot support:
  - event-driven surface recalculation
  - real-time GEX monitoring
  - live skew / term alerts
  - intraday portfolio risk refresh without polling loops outside the library

What is required to close it:

- exchange WebSocket connector
- snapshot + delta reconciliation model
- in-memory chain state
- periodic / event-driven surface rebuild logic
- reconnect / heartbeat / stale-state handling

### Gap 2: No strategy recommendation engine

Audit `1.0.0` expected:

- "which option structure for current vol regime"

Current `0.9.0` only provides descriptive analytics:

- regime labels
- term / skew metrics
- IV-vs-RV summary

Why this matters:

- the library can describe the market state but cannot translate that into:
  - long straddle vs short strangle bias
  - risk-reversal preference
  - calendar/diagonal preference
  - carry vs convexity tradeoff
  - hedge overlays

What is required to close it:

- strategy objects / templates
- structure-level Greek and scenario analytics
- rules or optimization logic mapping regime state to trade candidates
- configurable constraints on delta, vega, theta, tail exposure, and margin

### Gap 3: Documentation is solid engineering documentation, not yet a full trading guide

Audit `1.0.0` expected:

- comprehensive documentation
- API reference plus trading guide

Current docs are useful, but they are still mostly:

- package guides
- examples
- API-oriented explanations

What is missing for the audit's implied bar:

- market-structure guide for crypto options conventions
- hedging methodology guide
- treatment of contract multipliers / settlement specifics by venue
- explanation of dealer-sign assumptions in GEX
- caveats around interpolation vs calibrated surfaces
- operational guidance for research-to-production use

### Gap 4: Coverage / validation bar is below the audit's stated `95%+` aspiration

Current state:

- regression suite passes
- tests cover pricing, data fetch, historical vol, GEX, surface, portfolio

Missing relative to audit `1.0.0`:

- explicit coverage target and report
- benchmark pricing comparisons against trusted references
- stress tests on extreme parameter regions as a published validation artifact
- calibration/regression datasets for surface behavior
- live endpoint integration tests with resilient fixtures

For a senior quant developer, this is the difference between:

- "working library"
- "library with defendable validation package"

### Gap 5: The surface foundation is still below the maturity implied by an audit-style `1.0.0`

Strictly speaking, the audit placed SVI work earlier than `1.0.0`, but this still affects the `1.0.0` gap materially.

Current state:

- interpolation surface
- useful smile and term diagnostics
- report-ready export helpers

Missing:

- parametric calibration
- fit stability metrics
- arbitrage-aware surface regularization
- surface history comparison objects
- plotting / visualization layer inside the package

Why this matters:

- a streaming engine and strategy layer built on top of a weak surface representation will become fragile quickly
- `1.0.0` should likely stabilize the surface model before claiming production-ready status

### Gap 6: Data infrastructure is still light-duty relative to `1.0.0`

Current client is good enough for:

- research pulls
- periodic refresh
- examples and notebooks

It is not yet designed for:

- high-frequency polling
- many-underlying scaling
- persistent data service usage
- async concurrency
- historical market-state replay

This gap overlaps directly with the missing streaming layer.

### Gap 7: Repo governance / metadata cleanup is needed before `1.0.0`

Not explicitly in the audit, but required in practice:

- resolve license inconsistency
- align local dev environment and declared Python support
- decide whether publish should remain token-based or move to Trusted Publishing

These are not quant-model gaps, but they are real release-quality gaps.

## Recommended Interpretation Of Current State

If forced to map today's repo onto the audit roadmap, the most accurate statement is:

- all practical audit milestones through `0.4.0` are delivered
- some audit `1.0.0` scope is already delivered early:
  - portfolio analytics
  - package publishing
  - structured docs
- the true remaining work to claim an audit-style `1.0.0` is concentrated in:
  - live market-state infrastructure
  - strategy construction / recommendation
  - stronger validation / coverage posture
  - surface-model maturation
  - governance and metadata cleanup

So `v0.9.0` is not "almost nothing left". It is also not "far from useful". It is best described as:

- feature-complete for a research-grade vanilla crypto options analytics library
- not yet product-complete for the audit's production-platform vision

## Suggested Next Work If The Goal Is Audit `1.0.0`

Recommended order:

1. Resolve governance / packaging inconsistencies.
   - license cleanup
   - Python-version alignment
   - release/publish hardening
2. Decide surface strategy explicitly.
   - remain interpolation-first and document limits
   - or introduce SVI/SABR calibration as the stabilized surface core
3. Build live market-state infrastructure.
   - WebSocket connector
   - in-memory chain cache
   - rolling live surface rebuilds
4. Add strategy layer.
   - regime-to-structure mapping
   - structure analytics / constraints
5. Raise validation bar.
   - coverage report
   - benchmark test pack
   - numerical regression datasets

If those five are done, the repo will be much closer to the audit's intended `1.0.0` rather than merely a good `0.9.x`.
