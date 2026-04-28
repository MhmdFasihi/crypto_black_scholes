# crypto-bs

**Version 1.3.0** is a compatibility redirect package.

The maintained package is now **qerivative**:

```bash
pip install -U qerivative
```

```python
import qerivative as qd
```

`crypto-bs` remains available for legacy code. Importing `crypto_bs` now re-exports
the `qerivative` public API and emits a `DeprecationWarning`.

```python
import warnings

warnings.simplefilter("default", DeprecationWarning)

import crypto_bs

price = crypto_bs.price_option(
    50000,
    52000,
    30 / 365,
    0.8,
    "call",
    spec=crypto_bs.DERIBIT_BTC_INVERSE,
)
```

## Migration

- Replace `import crypto_bs` with `import qerivative as qd`.
- Replace submodule imports such as `crypto_bs.surface` with top-level `qerivative`
  imports where possible.
- `crypto_bs.__version__` reports the redirect package version (`1.3.0`).
- `qerivative.__version__` reports the maintained implementation version.

## Notes

- `crypto-bs` v1.x remains MIT licensed.
- `qerivative` is BSD-3-Clause licensed.
- No new implementation work lands in `crypto-bs`; new pricing, Greeks, surface,
  data, and risk functionality continues in `qerivative`.

See [CHANGELOG.md](CHANGELOG.md) for release notes.
