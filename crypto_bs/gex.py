"""Compatibility shim for qerivative.src.Analytics GEX helpers."""

from __future__ import annotations

from ._compat import warn_deprecated

warn_deprecated()

from qerivative.src.Analytics import compute_gex, find_gamma_flip, gex_summary  # noqa: E402,F401
