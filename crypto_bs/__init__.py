from .pricing import price_option, price_options_vectorized
from .greeks import delta, gamma, vega, theta, rho
from .utils import breakeven_price, breakeven_price_coin_based
from .data_fetch import (
    DeribitClient,
    get_available_instruments,
    get_btc_forward_price,
    get_btc_price,
    get_btc_volatility,
    get_full_chain,
    get_iv_surface_data,
    get_option_data,
)
from .historical_vol import (
    close_to_close_hv,
    parkinson_hv,
    rogers_satchell_hv,
    yang_zhang_hv,
    vol_premium,
)
from .gex import compute_gex, find_gamma_flip, gex_summary
from .analytics import VolatilityAnalytics
from .portfolio import (
    PortfolioAnalyzer,
    PortfolioDistribution,
    PortfolioPosition,
    PortfolioReport,
    build_portfolio_report,
    stress_test_portfolio,
)
from .surface import VolatilitySurface

# Advanced implementations
from .black_scholes import (
    BlackScholesModel, Black76Model, OptionParameters, OptionPricing,
    OptionType, PricingModel, price_coin_based_option, validate_deribit_pricing
)
from .greeks_calculator import (
    GreeksCalculator, GreeksProfile, PortfolioGreeks, RiskMetrics,
    calculate_option_greeks, analyze_portfolio_risk
)

__all__ = [
    '__version__',
    # Basic functions
    'price_option', 'price_options_vectorized', 'delta', 'gamma', 'vega', 'theta', 'rho',
    'breakeven_price',
    'breakeven_price_coin_based',
    'get_btc_forward_price', 'get_option_data', 'get_available_instruments',
    'get_btc_price', 'get_btc_volatility', 'get_full_chain', 'get_iv_surface_data',
    'close_to_close_hv', 'parkinson_hv', 'rogers_satchell_hv', 'yang_zhang_hv',
    'vol_premium',
    'compute_gex', 'find_gamma_flip', 'gex_summary', 'VolatilityAnalytics',
    'VolatilitySurface', 'DeribitClient',

    # Advanced classes
    'BlackScholesModel', 'Black76Model', 'OptionParameters', 'OptionPricing',
    'OptionType', 'PricingModel', 'GreeksCalculator', 'GreeksProfile',
    'PortfolioGreeks', 'RiskMetrics', 'PortfolioAnalyzer', 'PortfolioPosition',
    'PortfolioDistribution', 'PortfolioReport',

    # Advanced functions
    'price_coin_based_option', 'validate_deribit_pricing',
    'calculate_option_greeks', 'analyze_portfolio_risk',
    'build_portfolio_report', 'stress_test_portfolio',
]


__version__ = "0.8.0"
