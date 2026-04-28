"""Compatibility shim for qerivative.src.Pricing."""

from __future__ import annotations

from ._compat import warn_deprecated

warn_deprecated()

from qerivative.src.Pricing import *  # noqa: F401,F403,E402
