"""Compatibility shim for qerivative.src.Risk."""

from __future__ import annotations

from ._compat import warn_deprecated

warn_deprecated()

from qerivative.src.Risk import *  # noqa: F401,F403,E402
