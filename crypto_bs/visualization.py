"""Compatibility shim for qerivative.src.PlotFunctions."""

from __future__ import annotations

from ._compat import warn_deprecated

warn_deprecated()

from qerivative.src.PlotFunctions import *  # noqa: F401,F403,E402
