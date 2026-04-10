# Core Concepts

## Two pricing modes

`crypto_bs` supports two related but distinct models:

1. `price_option()` and the functions in `crypto_bs.pricing`
   They use Black-76 on a forward price `F` and return a coin-denominated premium.
2. `BlackScholesModel`
   It works off spot `S` and can return either standard USD premium or coin-based premium with `is_coin_based=True`.

## Delta naming matters

For coin-settled options, `0.2.0` split delta into two explicit fields:

- `delta_usd`
  Hedge delta, meaning `dV_usd / dS`.
- `delta_coin`
  Sensitivity of coin premium to spot, meaning `d(V_usd / S) / dS`.

If you are hedging, use `delta_usd`.

## Units and conventions

- `T` is always expressed in years.
- `sigma` is annualized volatility in decimal form, so `0.80` means `80%`.
- Coin-based option prices are fractions of the underlying coin.
- Historical-volatility helpers also return annualized decimal volatility.

## Option type handling

Across the public helpers, option types are usually strings:

- `"call"`
- `"put"`

The class-based engine also supports `OptionType.CALL` and `OptionType.PUT`.
