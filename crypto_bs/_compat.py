"""Shared helpers for the crypto_bs redirect package."""

from __future__ import annotations

import warnings


def warn_deprecated() -> None:
    warnings.warn(
        "crypto_bs is deprecated. Use qerivative instead.",
        DeprecationWarning,
        stacklevel=3,
    )
