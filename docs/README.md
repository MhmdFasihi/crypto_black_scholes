# crypto_bs Documentation

This directory contains the local documentation set for `crypto_bs`, organized as a practical developer guide for release `0.7.0`.

## Contents

- [Getting Started](guides/getting-started.md)
- [Core Concepts](guides/core-concepts.md)
- [Pricing Guide](guides/pricing-guide.md)
- [Risk and Greeks Guide](guides/risk-and-greeks.md)
- [Portfolio Risk Guide](guides/portfolio-risk-report.md)
- [Data and Market Inputs](guides/data-and-market-inputs.md)
- [Volatility Analytics](guides/volatility-analytics.md)
- [Volatility Surface Guide](guides/volatility-surface.md)
- [GEX Guide](guides/gex-guide.md)
- [Cookbook / Recipes](tutorials/cookbook.md)
- [API Reference](api/reference.md)

## Who should read what?

- New users: start at **Getting Started** and **Pricing Guide**.
- Traders/analysts: jump to **Risk and Greeks**, **Portfolio Risk Guide**, **Volatility Analytics**, and **GEX Guide**.
- Integrators: read **Data and Market Inputs** and **API Reference**.

## Version

This documentation targets **v0.7.0**.

## Notes

- The docs assume the package import name is `crypto_bs`.
- Market-data examples use public Deribit and CoinGecko endpoints; network failures propagate as normal `requests` or `ValueError` exceptions.
- For the change summary behind this docs set, see [../CHANGELOG.md](../CHANGELOG.md).
