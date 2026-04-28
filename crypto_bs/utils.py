"""Compatibility shim for qerivative.src.AuxFunctions."""

from __future__ import annotations

from ._compat import warn_deprecated

warn_deprecated()

from qerivative.src.AuxFunctions import *  # noqa: F401,F403,E402
