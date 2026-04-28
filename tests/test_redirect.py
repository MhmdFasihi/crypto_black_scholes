import importlib
import sys

import pytest


def _drop_crypto_bs_modules() -> None:
    for name in list(sys.modules):
        if name == "crypto_bs" or name.startswith("crypto_bs."):
            sys.modules.pop(name, None)


def test_crypto_bs_redirect_warns_and_imports_qerivative_api():
    _drop_crypto_bs_modules()

    with pytest.warns(DeprecationWarning, match="qerivative"):
        legacy = importlib.import_module("crypto_bs")

    assert legacy.__version__ == "1.3.0"
    assert legacy.VolatilitySurface.__name__ == "VolatilitySurface"
    assert legacy.SettlementType.LINEAR.value == "linear"


def test_legacy_submodule_redirect_warns():
    _drop_crypto_bs_modules()

    with pytest.warns(DeprecationWarning, match="qerivative"):
        pricing = importlib.import_module("crypto_bs.pricing")

    assert callable(pricing.price_option)
