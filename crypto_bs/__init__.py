"""Compatibility shim for the renamed qerivative package."""

from __future__ import annotations

from ._compat import warn_deprecated

warn_deprecated()

from qerivative import *  # noqa: F401,F403,E402
from qerivative import __all__ as _qerivative_all  # type: ignore[attr-defined] # noqa: E402

__version__ = "1.3.0"

__all__ = ["__version__", *_qerivative_all]
