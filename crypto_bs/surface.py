"""Compatibility shim for qerivative.src.Surface."""

from __future__ import annotations

from ._compat import warn_deprecated

warn_deprecated()

from qerivative.src.Surface import *  # noqa: F401,F403,E402
