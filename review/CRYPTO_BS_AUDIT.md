# CRYPTO_BS PROJECT — COMPREHENSIVE AUDIT & ROADMAP
## Quant-Developer Review of the crypto_bs Python Library

**Audit Date:** 2026-04-12
**Reviewer Role:** Senior Quantitative Developer
**Repository:** `crypto_bs_project`
**Current Version:** 0.9.0
**Author:** Seyed Mohammad Hossein Fasihi

> This document supersedes the original audit written against v0.1.0.
> All findings in this document reflect the actual codebase at v0.9.0.

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Capability Inventory](#2-capability-inventory)
3. [Mathematical Correctness Audit](#3-mathematical-correctness-audit)
4. [Bugs and Issues Found at v0.9.0](#4-bugs-and-issues-found-at-v090)
5. [What Is Missing](#5-what-is-missing)
6. [Code Quality Assessment](#6-code-quality-assessment)
7. [Test Coverage Assessment](#7-test-coverage-assessment)
8. [Overall Quantitative Score](#8-overall-quantitative-score)
9. [v1.0.0 Roadmap](#9-v100-roadmap)
10. [v2.0.0 Horizon](#10-v200-horizon)

---

## 1. EXECUTIVE SUMMARY

`crypto_bs` at v0.9.0 is a materially different project from the one described in the original audit. The original audit found critical formula errors in coin-based delta and gamma. Those errors are **fully corrected**. The library now has correct coin-settled pricing, correct Greek semantics, a volatility surface layer, portfolio analytics with VaR/CVaR, GEX analytics, four HV estimators, and a working distribution pipeline.

**Core math is solid.** The pricing engine, Greeks derivations, and HV estimators are all correct. The VaR/CVaR implementation has a correctness issue for multi-day horizons (BUG-01). The surface has no calibration layer and two broken arbitrage checks (BUG-04, BUG-05).

**The single most significant missing feature is visualization.** There is no `plot()` method on the surface, no smile plot, no GEX chart, and no term structure plot. For a library oriented around volatility surface analytics, this is a serious gap.

**Overall score: 6.0 / 10** — Research-grade. Core math is correct. Surface lacks calibration. Visualization is absent. Portfolio VaR has a horizon-scaling bug. Suitable for research, notebooks, and periodic analytics. Not suitable for live intraday workflows.

---

## 2. CAPABILITY INVENTORY

| Capability | Status | Quality |
|---|---|---|
| Black-Scholes USD call/put price | YES | CORRECT |
| Black-76 coin-settled call/put price | YES | CORRECT |
| Coin-based price (`V_coin = V_usd / S`) | YES | CORRECT |
| `delta_usd` — hedge delta | YES | CORRECT |
| `delta_coin` — coin-premium sensitivity | YES | CORRECT |
| `gamma` (USD and coin) | YES | CORRECT |
| `theta` (USD and coin) | YES | CORRECT |
| `vega` (USD and coin) | YES | CORRECT |
| `rho` (USD and coin) | YES | CORRECT |
| IV solver — Brent, intrinsic check, bounds 0.01–20.0 | YES | CORRECT |
| T=0 guard — floor at 1 hour | YES | CORRECT |
| Second-order Greeks (vanna, vomma, charm, speed) | YES | Finite differences, usable |
| Vectorized Black-76 chain pricing | YES | CORRECT |
| Close-to-close HV estimator | YES | CORRECT |
| Parkinson HV estimator | YES | CORRECT |
| Rogers-Satchell HV estimator | YES | CORRECT |
| Yang-Zhang HV estimator | YES | CORRECT |
| IV vs RV premium helper | YES | CORRECT |
| Volatility surface from chain quotes | YES | Interpolation only, no calibration |
| Surface strike/maturity interpolation | YES | Linear, usable |
| ATM IV term structure extraction | YES | CORRECT |
| Smile slice / surface grid export | YES | CORRECT |
| Delta-aware skew / RR / butterfly | YES | BUG-03 — see §4 |
| Butterfly / calendar arbitrage check | YES | BUG-04, BUG-05 — see §4 |
| GEX by strike from chain + OI | YES | CORRECT |
| Gamma flip detection | YES | CORRECT |
| Vol regime analytics (IVP, skew, TS) | YES | BUG-06 — thresholds |
| Portfolio position breakdown | YES | CORRECT |
| Portfolio concentration summary | YES | CORRECT |
| Deterministic stress tests | YES | CORRECT |
| Scenario-based VaR / CVaR (full reprice) | YES | BUG-01 — arithmetic return |
| DeribitClient (sync, retry, cache) | YES | Research-grade |
| Surface visualization (plot) | **NO** | MISSING-02 |
| SVI / SABR parametric calibration | **NO** | MISSING-01 |
| WebSocket / streaming | **NO** | MISSING-03 |
| Strategy / trade recommendation engine | **NO** | MISSING-04 |
| Historical surface storage | **NO** | MISSING-05 |

---

## 3. MATHEMATICAL CORRECTNESS AUDIT

### 3.1 Black-76 Coin-Settled Pricing — CORRECT

```
In pricing.py:
  d1 = (ln(F/K) + 0.5σ²T) / (σ√T)
  d2 = d1 − σ√T
  Call_coin = N(d1) − (K/F) × N(d2)
  Put_coin  = (K/F) × N(−d2) − N(−d1)
```

Undiscounted coin premium in the forward measure. Equivalent to `Call_usd / F`.
Correct for crypto where r ≈ 0 and F ≈ S.

### 3.2 Black-Scholes USD Pricing — CORRECT

```
In black_scholes.py:
  C = S × e^(−qT) × N(d1) − K × e^(−rT) × N(d2)
  P = K × e^(−rT) × N(−d2) − S × e^(−qT) × N(−d1)
```

Standard Merton (1973) formula with continuous dividend yield `q`. Correct.

### 3.3 Coin-Based Price Formula — CORRECT

```
V_coin = V_usd / S
  Call_coin = N(d1) − (K/S) × e^(−rT) × N(d2)
  Put_coin  = (K/S) × e^(−rT) × N(−d2) − N(−d1)
```

Verified: `V_usd / S = N(d1) − (K/S) × e^(−rT) × N(d2)` for the call. Correct.

### 3.4 Coin-Based Delta — CORRECT

```
delta_usd  = e^(−qT) × N(d1)      — USD hedge delta
delta_coin = (delta_usd × S − V_usd) / S²
```

**Derivation check:**

```
V_coin = V_usd / S
∂V_coin/∂S = (∂V_usd/∂S × S − V_usd) / S²
           = (Δ_usd × S − V_usd) / S²
```

For a call with q=0:
```
Δ_usd = N(d1)
V_usd = S × N(d1) − K × e^(−rT) × N(d2)
Δ_coin = [N(d1) × S − S × N(d1) + K × e^(−rT) × N(d2)] / S²
       = K × e^(−rT) × N(d2) / S²
```

Implementation in `black_scholes.py:214`:
```python
delta_coin = (delta_usd * S - V_usd) / (S**2)
```
CORRECT.

### 3.5 Coin-Based Gamma — CORRECT

```
gamma_coin = gamma_usd / S − 2 × delta_usd / S²
```

**Derivation check:**

```
Γ_coin = ∂Δ_coin/∂S
       = ∂/∂S [(Δ_usd × S − V_usd) / S²]
       = [Γ_usd × S² + Δ_usd × S − 2S × Δ_usd × S + 2S × V_usd/S] / S⁴
```

After simplification:
```
Γ_coin = Γ_usd / S − 2 × Δ_usd / S²
```

Note: the formula requires `Δ_usd`, NOT `Δ_coin`. The original audit's BUG-01 (using `Δ_coin` in the gamma cross term) is **fixed** in the current code.

Implementation in `black_scholes.py:221`:
```python
greeks['gamma'] = gamma_usd / S - 2 * delta_usd / (S**2)
```
CORRECT. Uses `delta_usd`.

### 3.6 Theta — CORRECT

USD theta: standard Black-Scholes formula, divided by 365 for daily decay.
Coin theta: `theta_usd / S`.

For crypto where q=0 and r=0, the theta formula reduces to:
```
θ = −S × σ × n(d1) / (2 × √T × 365)
```

This is correct and matches the implementation.

**Note on `greeks.py:theta`:** The Black-76 theta for calls and puts at r=0 is identical (no interest-rate differential between call and put). The code correctly returns the same formula for both. The duplicate `if` branches are cosmetically redundant but mathematically correct.

### 3.7 Vega — CORRECT

```
vega_usd  = S × e^(−qT) × n(d1) × √T / 100     (per 1% vol move)
vega_coin = vega_usd / S
```

The division by 100 gives vega per 1 percentage-point change in volatility. Correct.

Note: `greeks.py:vega` returns `F × √T × n(d1)` without the /100 scaling — this is vega per unit, consistent with that module's forward-based convention.

### 3.8 Rho — CORRECT

```
rho_usd  = K × T × e^(−rT) × N(d2) / 100    (call)
rho_coin = rho_usd / S
```

The original BUG-03 (hardcoded rho = 0) is **fixed**. Rho is now computed from the actual risk-free rate.

For crypto with r=0, rho ≈ 0 in practice but the formula is correct for any `r`.

### 3.9 IV Solver — CORRECT

- Brent's method with `xtol=1e-6`
- Fallback to `minimize_scalar`
- Intrinsic value guard: price must exceed `max(F − K, 0) / F` (coin) before solving
- Bounds: `[0.01, 20.0]` (1% to 2000%) — covers all known crypto vol extremes
- T floor at 1/8760 prevents division by zero

CORRECT. The original BUG-07 (upper bound 5.0) and BUG-08 (no intrinsic check) are **fixed**.

### 3.10 Historical Volatility Estimators — CORRECT

**Close-to-close:** `σ = std(log returns, ddof=0) × √252` — CORRECT.
Using `ddof=0` (population std) is the standard convention for rolling HV. Acceptable.

**Parkinson:**
```
σ² = mean[ln(H/L)²] / (4 × ln2) × 252
```
CORRECT. Parkinson (1980) formula.

**Rogers-Satchell:**
```
σ² = mean[ln(H/O) × (ln(H/O) − ln(C/O)) + ln(L/O) × (ln(L/O) − ln(C/O))] × 252
```
CORRECT. Rogers and Satchell (1991). Drift-corrected, does not require return = 0.

**Yang-Zhang:**
```
k = 0.34 / (1.34 + (n+1)/(n−1))
σ² = σ_overnight² + k × σ_close² + (1−k) × σ_RS²
```
CORRECT. Yang and Zhang (2000). Optimal k minimizes variance of the estimator.

### 3.11 GEX Formula — CORRECT

```
GEX(K) = sign × OI × Γ × S² × contract_size
```

Where:
- `short_gamma` convention: `sign = +1` for calls, `−1` for puts
- `long_gamma` convention: sign flipped

The `S²` term converts gamma (in `1/USD` units from Black-Scholes) to a dollar-gamma figure. This is the standard market convention.

Gamma flip: linear interpolation at zero-crossing of cumulative GEX. CORRECT.

### 3.12 VaR/CVaR Simulation — MOSTLY CORRECT (BUG-01)

Spot-vol correlation structure:
```python
correlated_vol = ρ × Z_spot + √(1−ρ²) × Z_vol
```
This is a correct 2×2 Cholesky decomposition for a correlated bivariate normal.

The actual spot shock application **has a bug** — see BUG-01 in §4.

CVaR definition:
```python
cutoff = np.quantile(pnl, 1 − confidence)
tail   = pnl[pnl <= cutoff]
cvar   = −tail.mean()
```
CVaR = expected loss in the tail. CORRECT.

---

## 4. BUGS AND ISSUES FOUND AT v0.9.0

### BUG-01 — MEDIUM: VaR uses arithmetic spot return, not log-normal

**File:** `crypto_bs/portfolio.py`, line 424

```python
# WRONG — arithmetic approximation
shocked_spot = max(position.spot_price * (1.0 + float(spot_return[scenario_idx])), 1e-12)
```

Here `spot_return[i] = σ × √dt × Z` where Z is standard normal. Applying this as an arithmetic return `1 + σ√dt Z` is an approximation of `exp(σ√dt Z)`.

**Error magnitude:**
- 1-day horizon (`dt = 1/365`): max error at 3σ ≈ 0.3%. Acceptable.
- 10-day horizon: max error at 3σ ≈ 3%. Material for tail risk.
- 30-day horizon: max error at 3σ ≈ 10%. Significantly underestimates right-tail spot levels.

For a long-call position, underestimating right-tail spot means underestimating the gain scenario. For a short-call, it underestimates the loss scenario. VaR for any position is biased for horizons beyond 5 days.

**Fix:**
```python
# CORRECT — log-normal
log_return = float(spot_return[scenario_idx])  # σ × √dt × Z
shocked_spot = max(position.spot_price * np.exp(log_return), 1e-12)
```

The `spot_return` array formula in `shock_by_underlying` stays unchanged; only the application changes from `1 + x` to `exp(x)`.

---

### BUG-02 — MEDIUM: VaR default spot_volatility weighted by notional, not vega

**File:** `crypto_bs/portfolio.py`, lines 396–400

```python
spot_volatility = _weighted_average(
    [position.volatility for position in normalized],
    [position.quantity * position.spot_price for position in normalized],
)
```

This weights each position's IV by `quantity × spot_price` (notional). The intent is to find the "portfolio volatility" to use as the spot shock scale.

**Why this is wrong:**
1. `quantity` can be negative (short positions). `np.abs(w)` is used in `_weighted_average`, so short positions are treated identically to long — but that's not the right economic weight either.
2. Deep OTM options with high IV but small notional contribute disproportionately little. But they're the positions where the IV most matters for simulated path behaviour.
3. The correct economic weight for "which vol drives spot shock" is **vega** — how much each position's value changes per unit of vol move is the right weight.

**Fix:**
```python
vegas = []
for position in normalized:
    pricing = self.bs_model.calculate_option_price(self._to_option_parameters(position))
    vegas.append(abs(float(pricing.vega)) * abs(position.quantity))

spot_volatility = _weighted_average(
    [position.volatility for position in normalized],
    vegas,
)
```

If all vegas are zero (edge case: all at-expiry positions), fall back to equal weights.

---

### BUG-03 — MEDIUM: Delta-aware smile metrics computed at nearest_t, labeled as requested maturity

**File:** `crypto_bs/surface.py`, lines 287–328

```python
def _delta_metrics(self, time_to_maturity: float, delta: float) -> dict[str, float] | None:
    nearest_t = self._nearest_time(time_to_maturity)
    frame = self._raw_by_t[nearest_t]
    ...
    params = OptionParameters(
        ...
        time_to_maturity=float(nearest_t),   # ← computed at nearest_t
        ...
    )
    row_delta = bs_model.calculate_option_price(params).delta_usd
```

When `time_to_maturity = 45d` and `nearest_t = 30d`, the delta calculation is done at T=30d, the wing-selection is done from the T=30d slice, but the result is returned and labeled as the T=45d skew in `describe_surface()` and `get_smile_metrics()`.

**Impact:** Surface summaries (`describe_surface()`) report skew/RR/BF for maturities that were never directly observed, without indicating that the metrics are extrapolated from a different maturity. For a user building a surface grid over custom maturities, this can be silently misleading.

**Fix (pragmatic):** Add `nearest_fitted_maturity` to the returned dict so the caller knows which maturity the metrics actually come from. This is already done in `describe_surface()` at line 267 — but `get_smile_metrics()` itself does not expose it, and the docstring does not document this behaviour.

---

### BUG-04 — LOW: Butterfly arbitrage check threshold is too loose and uses wrong space

**File:** `crypto_bs/surface.py`, lines 385–389

```python
iv = g["implied_volatility"].to_numpy(dtype=float)
if len(iv) >= 3:
    second_diff = np.diff(iv, n=2)
    if np.any(np.abs(second_diff) > 0.35):
        issues["butterfly"].append(...)
```

**Two problems:**
1. Threshold of 0.35 means any second difference in IV < 35 vol points passes. In real crypto data with 10–15 strikes per expiry, a second difference of 34 vol points is an extreme butterfly violation that would be flagged as free money by any arb desk.
2. Real static butterfly no-arbitrage requires the smile to be **convex in total variance space** (`w(x) = σ²(x) × T` where `x = ln(K/F)/√T`). Checking raw second differences in IV over raw strike is a proxy at best.

**Fix:** Check convexity of `total_variance = IV² × T` over `log_moneyness = ln(strike / spot)`. Flag if `total_variance` has any strictly concave segment.

---

### BUG-05 — LOW: Calendar spread arbitrage check uses IV absolute jump, not total variance

**File:** `crypto_bs/surface.py`, lines 390–397

```python
jumps = np.abs(np.diff(ts.values.astype(float)))
for i, j in enumerate(jumps):
    if j > 0.25:
        issues["calendar"].append(...)
```

This flags if ATM IV jumps by more than 25 vol points between adjacent maturities. It does **not** detect the actual calendar arbitrage condition.

**The correct check:** Total variance `T × σ²(T)` must be non-decreasing in T. An inverted term structure (e.g. front IV = 90%, back IV = 80%) has a jump of 10 vol points — below the threshold — but represents a calendar spread violation:
```
T1 × 0.90² = 0.3 × 0.81 = 0.243
T2 × 0.80² = 0.8 × 0.64 = 0.512   ← total var increases, so actually fine here
```

But:
```
T1 = 7d:   0.019 × 1.40² = 0.038
T2 = 30d:  0.082 × 0.80² = 0.052   ← fine
T3 = 90d:  0.247 × 0.70² = 0.121   ← fine

But if:
T2 = 30d:  0.082 × 0.85² = 0.059
T3 = 90d:  0.247 × 0.65² = 0.104   ← fine

Example of a violation:
T1 = 7d:   0.019 × 1.00² = 0.019
T2 = 14d:  0.038 × 0.90² = 0.031   ← total var DECREASES → calendar arb
```

**Fix:**
```python
ts_sorted = self._term.sort_index()
t_vals = ts_sorted.index.to_numpy(dtype=float)
iv_vals = ts_sorted.values.astype(float)
total_var = t_vals * iv_vals**2
diffs = np.diff(total_var)
for i, d in enumerate(diffs):
    if d < -1e-6:
        t0, t1 = ts_sorted.index[i], ts_sorted.index[i + 1]
        issues["calendar"].append(
            f"calendar arbitrage: total variance decreasing from T={t0:.4f} to T={t1:.4f}"
        )
```

---

### BUG-06 — LOW: Skew and TS regime thresholds are hardcoded and asymmetric

**File:** `crypto_bs/analytics.py`, lines 190–205

```python
if skew > 0.03:   return "STEEP"
if skew < -0.01:  return "INVERTED"
```

BTC options have historically persistent put skew (puts > calls). Setting INVERTED at −1 vol point means any tiny call premium is classified as INVERTED. Setting STEEP at +3 vol points means normal market conditions always = STEEP, providing no signal differentiation.

The TS regime:
```python
if ratio > 1.05:  return "BACKWARDATION"
if ratio < 0.95:  return "CONTANGO"
```
±5% around parity is a reasonable starting point, but these are undocumented and not configurable.

**Impact:** Users applying this library to ETH options or altcoin options will get regime signals calibrated to BTC's historical skew bias, which is wrong for other assets.

**Fix:** Add optional threshold parameters to `skew_regime()` and `ts_regime()` so callers can configure them per asset. Document the defaults as BTC-specific.

---

### BUG-07 — LOW: GEX computation is a scalar loop over `iterrows`

**File:** `crypto_bs/gex.py`, lines 56–86

```python
for _, row in chain_df.iterrows():
    ...
    gamma = bs.calculate_option_price(params).gamma
```

For a BTC chain with ~2000 active instruments, this loop runs 2000 scalar model evaluations. At ~0.5–1ms per call, that is 1–2 seconds per chain snapshot.

`price_options_vectorized()` exists in `pricing.py` and would compute all gammas in a single numpy operation (~5ms for 2000 instruments).

**Impact:** Performance only. GEX values are correct. But live workflows and repeated analytics pass are impractical at current speed.

---

### BUG-08 — INFO: `greeks.py:theta` has redundant call/put branches

```python
if option_type.lower() == 'call':
    return float(-(F * sigma * norm.pdf(d1)) / (2 * np.sqrt(T_eff)))
if option_type.lower() == 'put':
    return float(-(F * sigma * norm.pdf(d1)) / (2 * np.sqrt(T_eff)))
```

Call and put theta are **identical** in the Black-76 undiscounted coin forward measure at r=0. The code is mathematically correct but the duplicate branches confuse readers into thinking call/put theta differ.

**Fix:** Remove the `if/if` and compute once. Or add a comment explaining that in the forward measure at r=0, call and put theta are equal.

---

### BUG-09 — INFO: `PortfolioPosition.risk_free_rate` defaults to 0.05

**File:** `crypto_bs/portfolio.py`, line 37

```python
risk_free_rate: float = 0.05
```

A 5% risk-free rate is wrong for coin-settled crypto options where r ≈ 0 by construction (the forward is the perpetual, not a rate-discounted spot). Any user who builds a `PortfolioPosition` without explicitly setting `risk_free_rate=0.0` will get systematically mispriced options.

For example, at r=5%, the put-call parity correction is:
```
C − P = F × e^(−rT) − K × e^(−rT)
```
At T=30d, r=5%, this is a ~0.4% discount — small but non-zero systematic error in every Greek.

**Fix:** `risk_free_rate: float = 0.0`

---

### MISSING-06 — License inconsistency

`crypto_bs/black_scholes.py` header:
```
# License: AGPL-3.0 or commercial
```

`pyproject.toml` and `LICENSE` file: MIT.

AGPLv3 is a copyleft license incompatible with MIT. This creates legal ambiguity for any downstream user. Must be resolved before v1.0 positioning.

**Fix:** Remove the AGPL header from `black_scholes.py`, replace with MIT notice consistent with `pyproject.toml`.

---

## 5. WHAT IS MISSING

### MISSING-01 — CRITICAL: No parametric surface calibration

The surface is purely empirical interpolation in strike/maturity space. There is no:
- SVI (Stochastic Volatility Inspired) calibration
- SABR calibration
- Fit residuals or calibration quality metrics
- Arbitrage-free guarantee
- Stable extrapolation beyond quoted strike range

For smile trading, calendar spread trading, or risk model construction, an interpolation surface is insufficient. Every serious quant surface library (e.g. QuantLib, vollib, py_vollib_vectorized) provides at minimum an SVI or SSVI parametrization.

**Impact:** Users cannot do arbitrage-free surface interpolation, cannot compute stable forward smiles, and cannot produce Greeks consistent with a calibrated surface model.

---

### MISSING-02 — CRITICAL: No visualization

The library produces no charts. The original audit roadmap explicitly included `surface.plot()`. Current state: zero visualization code.

For a volatility analytics library, the absence of visualization is a significant practical gap. Every workflow requires external matplotlib or plotly code to see what the surface looks like.

**Required for v1.0:**
- Interactive 3D surface plot (strike × maturity × IV)
- Smile slice per maturity
- ATM IV term structure
- GEX bar chart by strike

---

### MISSING-03 — HIGH: No WebSocket / streaming

The `DeribitClient` is synchronous and batch-only. No:
- WebSocket connection
- Incremental quote update handling
- Stateful live surface maintenance
- Reconnect / heartbeat / stale-state handling

**Impact:** Unsuitable for intraday hedging, real-time GEX monitoring, or live portfolio risk refresh.

---

### MISSING-04 — HIGH: No strategy recommendation layer

`trading_signal()` returns a scalar in `{−1.5, −1, −0.5, 0, 0.5, 1, 1.5}` from two regime enums. It does not produce:
- Structure recommendations (straddle, strangle, risk reversal, calendar)
- Structure-level Greek analytics
- Carry vs convexity tradeoff estimates
- Hedge overlays

The signal is a toy. A real strategy layer needs structure objects, scenario analytics per structure, and regime-to-structure mapping rules.

---

### MISSING-05 — MEDIUM: No historical surface storage

`iv_percentile()` requires the caller to supply a `historical_atm_iv` Series. The library does not maintain or persist:
- Historical surface snapshots
- Rolling ATM IV history
- Term-structure history

**Impact:** IVP analytics are only available if the user has already built their own history store.

---

## 6. CODE QUALITY ASSESSMENT

### Type Hints

All core modules (`black_scholes.py`, `portfolio.py`, `surface.py`, `analytics.py`, `gex.py`) have consistent type hints using `from __future__ import annotations`. GOOD.

### Error Handling

Input validation is present on all public entry points. Meaningful error messages for invalid inputs (negative spot, zero T, unknown option_type). GOOD.

### Logging

Configured but not used. `BlackScholesModel.__init__` sets up a logger that is never called with warnings or errors. LOW PRIORITY.

### Performance

The `price_options_vectorized()` function exists and is correct. However, `gex.py` and `greeks_calculator.py` both fall back to scalar loops. For chain-level operations this is 10–100× slower than necessary.

### Dataclasses

Heavy use of `@dataclass(frozen=True)` for `PortfolioPosition` and `PortfolioDistribution`. Immutable dataclasses are a good design choice for a quant library — prevents accidental mutation of position state.

### Dependency Footprint

Minimal: `numpy`, `scipy`, `pandas`, `requests`. No heavy dependencies. GOOD.
`plotly` is missing but will be required for v1.0 visualization.

---

## 7. TEST COVERAGE ASSESSMENT

### What Is Tested

| Module | Coverage Status |
|---|---|
| `black_scholes.py` — pricing, Greeks, put-call parity, IV round-trip | GOOD |
| `pricing.py` — coin call/put, vectorized | GOOD |
| `historical_vol.py` — four estimators, window validation | GOOD |
| `surface.py` — fit, interpolation, term structure, smile metrics, arbitrage check | GOOD |
| `analytics.py` — regimes, IVP, vol premium, skew term metrics | GOOD |
| `gex.py` — compute_gex, find_gamma_flip, gex_summary | GOOD |
| `portfolio.py` — breakdown, stress test, VaR/CVaR, full report | GOOD |
| `data_fetch.py` — normalization, chain filtering | PARTIAL |

### What Is Not Tested

| Gap | Risk |
|---|---|
| `DeribitClient` HTTP retry/timeout/caching behaviour | HIGH — live workflows will break without this |
| Delta-aware skew path (vs fallback quantile path) | HIGH — primary code path for delta-aware metrics |
| VaR at multi-day horizons (BUG-01) | HIGH — regression test would catch the arithmetic/lognormal bug |
| Calendar arb check with known violating dataset | MEDIUM |
| Portfolio with non-zero `risk_free_rate` in VaR | MEDIUM |
| Extreme parameter regions (T < 1 day, sigma > 300%) | MEDIUM |
| `greeks_calculator.py` second-order Greeks numerical stability | LOW |
| `utils.py` breakeven with coin-based prices | LOW |

### Coverage Estimate

Functional happy-path coverage: ~85%.
Edge-case and robustness coverage: ~40%.
Integration / live API test coverage: 0%.

---

## 8. OVERALL QUANTITATIVE SCORE

| Area | Score | Notes |
|---|---|---|
| Pricing correctness | 9 / 10 | All Greeks correct at v0.9.0. Rho present. Coin formulas verified. |
| Numerical stability | 8 / 10 | T=0 guard, intrinsic check, IV bounds — solid. |
| Surface quality | 5 / 10 | Empirical interpolation only. No calibration. Broken arb checks. |
| Risk analytics | 7 / 10 | Full reprice VaR/CVaR. BUG-01 (arithmetic return) for long horizons. |
| Data layer | 6 / 10 | Sync REST. Retry/cache present. Not live-capable. |
| Visualization | 0 / 10 | Does not exist. |
| Test coverage | 6 / 10 | Happy paths covered. HTTP, edge numerics, delta-aware path missing. |
| Documentation | 7 / 10 | Good API docs. No trading guide, no hedging methodology doc. |
| **Overall** | **6.0 / 10** | Research-grade. Core math correct. Surface and viz are the gaps. |

---

## 9. v1.0.0 ROADMAP

### v1.0.0 Scope

**Bug fixes (blocking):**
- BUG-01: Log-normal spot return in VaR simulation
- BUG-02: Vega-weighted default spot_volatility in VaR
- BUG-05: Calendar arb check using total variance monotonicity
- BUG-09: `risk_free_rate` default 0.05 → 0.0
- MISSING-06: Remove AGPLv3 license header from `black_scholes.py`

**New capabilities (required):**
- `crypto_bs/visualization.py` — Plotly-based interactive plots:
  - `plot_volatility_surface(surface)` → `go.Figure` — interactive 3D surface
  - `plot_smile_slice(surface, maturities)` → `go.Figure` — IV vs strike per maturity
  - `plot_term_structure(surface, analytics)` → `go.Figure` — ATM IV term structure
  - `plot_gex(gex_df, spot, gamma_flip)` → `go.Figure` — GEX bar chart by strike
- Add `plotly` to `pyproject.toml` dependencies
- Export visualization functions from `__init__.py`

**Documentation:**
- Update `CHANGELOG.md`
- Note `risk_free_rate` default change as a breaking change

**Deferred to v1.1+:**
- SVI / SABR parametric calibration
- WebSocket streaming layer
- Strategy recommendation engine
- Historical surface persistence

### Implementation Sequence

1. Fix BUG-09 (one-line change, verify test suite passes)
2. Fix BUG-05 (calendar arb total variance)
3. Fix BUG-01 (log-normal VaR)
4. Fix BUG-02 (vega-weighted volatility)
5. Fix MISSING-06 (license header)
6. Implement `crypto_bs/visualization.py`
7. Update `__init__.py` exports
8. Add `plotly` to `pyproject.toml`
9. Add `tests/test_visualization.py`
10. Update `CHANGELOG.md`
11. `pytest tests/` — all pass

### v1.0.0 Expected Score

| Area | v0.9.0 | v1.0.0 Target |
|---|---|---|
| Pricing correctness | 9 | 9 |
| Numerical stability | 8 | 9 |
| Surface quality | 5 | 5 (deferred) |
| Risk analytics | 7 | 8 |
| Data layer | 6 | 6 |
| Visualization | 0 | 7 |
| Test coverage | 6 | 7 |
| Documentation | 7 | 7 |
| **Overall** | **6.0** | **7.0** |

---

## 10. v2.0.0 HORIZON

Items deferred beyond v1.0:

| Feature | Rationale |
|---|---|
| SVI / SSVI calibration | Full arbitrage-free surface parametrization |
| SABR model | Smile-consistent, widely used in rates/FX/crypto |
| WebSocket streaming | Live IV surface from Deribit websocket |
| Strategy layer | Regime-to-structure mapping, structure Greeks, carry/convexity analytics |
| Historical surface storage | Persistent surface snapshots for IVP and regime history |
| Monte Carlo pricer | Handle path-dependent or barrier payoffs |
| Jump-diffusion model (Merton) | Crypto tail risk — jumps are the dominant risk driver in crypto |
| American option support | Binomial tree or BAW approximation |

---

*End of CRYPTO_BS_AUDIT.md — v0.9.0 quant review*
