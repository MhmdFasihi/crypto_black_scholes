# Copyright (c) 2025 Seyed Mohammad Hossein Fasihi (Mhmd Fasihi)
# This file is part of a project licensed under AGPLv3 or a commercial license.
# AGPLv3: https://www.gnu.org/licenses/agpl-3.0.html
# Contact for commercial licensing: mhmd.fasihi@gmail.com

"""
Black-Scholes Model Implementation with Coin-Based Pricing Support
Supports both standard (USD) and cryptocurrency-denominated options
"""

import numpy as np
from scipy.stats import norm
from scipy.optimize import minimize_scalar, brentq
from typing import Dict, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta

# Import your fixed time utilities
import sys
import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# from src.core.utils.time_utils import TimeUtils  # Commented out - not available in this project

logger = logging.getLogger(__name__)


class OptionType(Enum):
    """Option type enumeration."""
    CALL = "call"
    PUT = "put"


class PricingModel(Enum):
    """Pricing model types."""
    BLACK_SCHOLES = "black_scholes"  # Standard Black-Scholes
    BLACK_76 = "black_76"  # For futures options
    COIN_BASED = "coin_based"  # Crypto-denominated options


@dataclass
class OptionParameters:
    """Parameters for option pricing."""
    spot_price: float
    strike_price: float
    time_to_maturity: float  # In years
    volatility: float  # Annualized
    risk_free_rate: float = 0.05
    dividend_yield: float = 0.0  # For crypto, this could be staking yield
    option_type: Union[OptionType, str] = OptionType.CALL
    pricing_model: PricingModel = PricingModel.BLACK_SCHOLES
    is_coin_based: bool = False  # True for BTC/ETH denominated options


@dataclass
class OptionPricing:
    """Results from option pricing calculations."""
    option_price: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    intrinsic_value: float
    time_value: float
    moneyness: float  # S/K ratio
    coin_based_price: Optional[float] = None  # Price in crypto terms
    usd_price: Optional[float] = None  # Price in USD terms


class BlackScholesModel:
    """
    Black-Scholes model with support for coin-based pricing.
    
    For coin-based options (like on Deribit):
    - Premium is paid in the underlying cryptocurrency
    - Settlement is in cryptocurrency
    - We need to adjust the standard formulas
    """
    
    def __init__(self, min_time_to_maturity: float = 1/365):
        """
        Initialize Black-Scholes model.
        
        Args:
            min_time_to_maturity: Minimum time to maturity (default 1 day)
        """
        self.min_time_to_maturity = min_time_to_maturity
        self.logger = logging.getLogger(__name__)
    
    def calculate_option_price(self, params: OptionParameters) -> OptionPricing:
        """
        Calculate option price and Greeks.
        
        Args:
            params: Option parameters
            
        Returns:
            Complete option pricing results
        """
        # Validate parameters
        self._validate_parameters(params)
        
        # Extract parameters
        S = params.spot_price
        K = params.strike_price
        T = max(params.time_to_maturity, self.min_time_to_maturity)
        σ = params.volatility
        r = params.risk_free_rate
        q = params.dividend_yield
        option_type = params.option_type.value if isinstance(params.option_type, OptionType) else params.option_type
        
        # Calculate d1 and d2
        d1, d2 = self._calculate_d1_d2(S, K, T, r, σ, q)
        
        # Calculate option price based on model
        if params.is_coin_based:
            # Coin-based pricing (premium in crypto)
            option_price = self._calculate_coin_based_price(S, K, T, r, σ, q, d1, d2, option_type)
            coin_based_price = option_price
            usd_price = option_price * S  # Convert to USD equivalent
        else:
            # Standard Black-Scholes (premium in USD)
            if option_type.lower() == 'call':
                option_price = self._call_price(S, K, T, r, σ, q, d1, d2)
            else:
                option_price = self._put_price(S, K, T, r, σ, q, d1, d2)
            usd_price = option_price
            coin_based_price = option_price / S  # Convert to crypto equivalent
        
        # Calculate Greeks (adjusted for coin-based if needed)
        greeks = self._calculate_greeks(S, K, T, r, σ, q, d1, d2, option_type, params.is_coin_based)
        
        # Calculate additional metrics
        intrinsic_value = self._calculate_intrinsic_value(S, K, option_type)
        if params.is_coin_based:
            intrinsic_value = intrinsic_value / S  # Convert to coin terms
        
        time_value = option_price - intrinsic_value
        moneyness = S / K
        
        return OptionPricing(
            option_price=option_price,
            delta=greeks['delta'],
            gamma=greeks['gamma'],
            theta=greeks['theta'],
            vega=greeks['vega'],
            rho=greeks['rho'],
            intrinsic_value=intrinsic_value,
            time_value=time_value,
            moneyness=moneyness,
            coin_based_price=coin_based_price,
            usd_price=usd_price
        )
    
    def _calculate_d1_d2(self, S: float, K: float, T: float, r: float, σ: float, q: float) -> Tuple[float, float]:
        """Calculate d1 and d2 for Black-Scholes formula."""
        d1 = (np.log(S / K) + (r - q + 0.5 * σ**2) * T) / (σ * np.sqrt(T))
        d2 = d1 - σ * np.sqrt(T)
        return d1, d2
    
    def _call_price(self, S: float, K: float, T: float, r: float, σ: float, q: float, d1: float, d2: float) -> float:
        """Calculate call option price (standard Black-Scholes)."""
        return S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    def _put_price(self, S: float, K: float, T: float, r: float, σ: float, q: float, d1: float, d2: float) -> float:
        """Calculate put option price (standard Black-Scholes)."""
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
    
    def _calculate_coin_based_price(self, S: float, K: float, T: float, r: float, σ: float, q: float, 
                                   d1: float, d2: float, option_type: str) -> float:
        """
        Calculate coin-based option price (premium in cryptocurrency).
        
        For coin-based options:
        - The premium is denominated in the underlying cryptocurrency
        - This is common for crypto options on exchanges like Deribit
        - The formula is adjusted: divide standard price by spot price
        """
        if option_type.lower() == 'call':
            # Coin-based call: C_coin = (S*N(d1) - K*exp(-r*T)*N(d2)) / S
            # Simplifies to: N(d1) - (K/S)*exp(-r*T)*N(d2)
            price = norm.cdf(d1) - (K/S) * np.exp(-r * T) * norm.cdf(d2)
        else:
            # Coin-based put: P_coin = (K*exp(-r*T)*N(-d2) - S*N(-d1)) / S
            # Simplifies to: (K/S)*exp(-r*T)*N(-d2) - N(-d1)
            price = (K/S) * np.exp(-r * T) * norm.cdf(-d2) - norm.cdf(-d1)
        
        return max(price, 0)  # Ensure non-negative
    
    def _calculate_greeks(self, S: float, K: float, T: float, r: float, σ: float, q: float,
                         d1: float, d2: float, option_type: str, is_coin_based: bool) -> Dict[str, float]:
        """
        Calculate all Greeks with adjustments for coin-based options.
        """
        greeks = {}
        
        # Common calculations
        sqrt_T = np.sqrt(T)
        pdf_d1 = norm.pdf(d1)
        
        # Delta
        if option_type.lower() == 'call':
            delta_usd = np.exp(-q * T) * norm.cdf(d1)
        else:
            delta_usd = -np.exp(-q * T) * norm.cdf(-d1)
        
        if is_coin_based:
            # Adjust delta for coin-based options
            # Delta_coin = ∂(Price_coin)/∂S = ∂(Price_usd/S)/∂S
            if option_type.lower() == 'call':
                greeks['delta'] = (K * np.exp(-r * T) * norm.cdf(d2)) / (S**2)
            else:
                greeks['delta'] = -(K * np.exp(-r * T) * norm.cdf(-d2)) / (S**2)
        else:
            greeks['delta'] = delta_usd
        
        # Gamma (needs adjustment for coin-based)
        gamma_usd = np.exp(-q * T) * pdf_d1 / (S * σ * sqrt_T)
        if is_coin_based:
            # Gamma for coin-based options requires second derivative adjustment
            greeks['gamma'] = gamma_usd / S - 2 * greeks['delta'] / S
        else:
            greeks['gamma'] = gamma_usd
        
        # Theta (per day, needs adjustment for coin-based)
        theta_term1 = -(S * np.exp(-q * T) * pdf_d1 * σ) / (2 * sqrt_T)
        if option_type.lower() == 'call':
            theta_term2 = r * K * np.exp(-r * T) * norm.cdf(d2)
            theta_term3 = -q * S * np.exp(-q * T) * norm.cdf(d1)
        else:
            theta_term2 = -r * K * np.exp(-r * T) * norm.cdf(-d2)
            theta_term3 = q * S * np.exp(-q * T) * norm.cdf(-d1)
        
        theta_usd = (theta_term1 - theta_term2 + theta_term3) / 365  # Convert to daily
        
        if is_coin_based:
            greeks['theta'] = theta_usd / S
        else:
            greeks['theta'] = theta_usd
        
        # Vega (per 1% change in volatility)
        vega_usd = S * np.exp(-q * T) * pdf_d1 * sqrt_T / 100
        if is_coin_based:
            greeks['vega'] = vega_usd / S
        else:
            greeks['vega'] = vega_usd
        
        # Rho (per 1% change in interest rate)
        if option_type.lower() == 'call':
            rho_usd = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
        else:
            rho_usd = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
        
        if is_coin_based:
            greeks['rho'] = rho_usd / S
        else:
            greeks['rho'] = rho_usd
        
        return greeks
    
    def _calculate_intrinsic_value(self, S: float, K: float, option_type: str) -> float:
        """Calculate intrinsic value."""
        if option_type.lower() == 'call':
            return max(S - K, 0)
        else:  # put
            return max(K - S, 0)
    
    def _validate_parameters(self, params: OptionParameters) -> None:
        """Validate option parameters."""
        if params.spot_price <= 0:
            raise ValueError("Spot price must be positive")
        if params.strike_price <= 0:
            raise ValueError("Strike price must be positive")
        if params.time_to_maturity < 0:
            raise ValueError("Time to maturity cannot be negative")
        if params.volatility <= 0:
            raise ValueError("Volatility must be positive")
    
    def calculate_implied_volatility(self, market_price: float, params: OptionParameters,
                                    min_vol: float = 0.01, max_vol: float = 5.0) -> float:
        """
        Calculate implied volatility using Newton-Raphson method.
        
        Args:
            market_price: Observed market price
            params: Option parameters (without volatility)
            min_vol: Minimum volatility bound
            max_vol: Maximum volatility bound
            
        Returns:
            Implied volatility
        """
        def objective(vol):
            params_copy = OptionParameters(
                spot_price=params.spot_price,
                strike_price=params.strike_price,
                time_to_maturity=params.time_to_maturity,
                volatility=vol,
                risk_free_rate=params.risk_free_rate,
                dividend_yield=params.dividend_yield,
                option_type=params.option_type,
                is_coin_based=params.is_coin_based
            )
            theoretical_price = self.calculate_option_price(params_copy).option_price
            return theoretical_price - market_price
        
        try:
            # Use Brent's method for robustness
            iv = brentq(objective, min_vol, max_vol, xtol=1e-6)
            return iv
        except ValueError:
            # If Brent's method fails, try minimize_scalar
            result = minimize_scalar(lambda v: abs(objective(v)), 
                                    bounds=(min_vol, max_vol), 
                                    method='bounded')
            return result.x


class Black76Model(BlackScholesModel):
    """
    Black-76 model for futures options.
    Used for cryptocurrency futures options.
    """
    
    def _calculate_d1_d2(self, F: float, K: float, T: float, r: float, σ: float, q: float = 0) -> Tuple[float, float]:
        """Calculate d1 and d2 for Black-76 formula (using futures price)."""
        d1 = (np.log(F / K) + (0.5 * σ**2) * T) / (σ * np.sqrt(T))
        d2 = d1 - σ * np.sqrt(T)
        return d1, d2
    
    def _call_price(self, F: float, K: float, T: float, r: float, σ: float, q: float, d1: float, d2: float) -> float:
        """Calculate call option price (Black-76)."""
        return np.exp(-r * T) * (F * norm.cdf(d1) - K * norm.cdf(d2))
    
    def _put_price(self, F: float, K: float, T: float, r: float, σ: float, q: float, d1: float, d2: float) -> float:
        """Calculate put option price (Black-76)."""
        return np.exp(-r * T) * (K * norm.cdf(-d2) - F * norm.cdf(-d1))


# Utility functions for quick calculations
def price_coin_based_option(spot: float, strike: float, time_to_maturity: float,
                           volatility: float, option_type: str = 'call',
                           risk_free_rate: float = 0.05) -> Dict[str, float]:
    """
    Quick pricing function for coin-based options.
    
    Returns both coin-based and USD prices.
    """
    bs_model = BlackScholesModel()
    
    params = OptionParameters(
        spot_price=spot,
        strike_price=strike,
        time_to_maturity=time_to_maturity,
        volatility=volatility,
        risk_free_rate=risk_free_rate,
        option_type=OptionType.CALL if option_type.lower() == 'call' else OptionType.PUT,
        is_coin_based=True
    )
    
    result = bs_model.calculate_option_price(params)
    
    return {
        'coin_price': result.coin_based_price,
        'usd_price': result.usd_price,
        'delta': result.delta,
        'gamma': result.gamma,
        'theta': result.theta,
        'vega': result.vega,
        'rho': result.rho
    }


def validate_deribit_pricing(deribit_price_btc: float, spot: float, strike: float,
                            time_to_maturity: float, option_type: str = 'call') -> Dict[str, float]:
    """
    Validate Deribit pricing by calculating implied volatility.
    
    Args:
        deribit_price_btc: Deribit price in BTC
        spot: Current BTC spot price in USD
        strike: Strike price in USD
        time_to_maturity: Time to maturity in years
        option_type: 'call' or 'put'
        
    Returns:
        Dictionary with implied volatility and theoretical prices
    """
    bs_model = BlackScholesModel()
    
    # Create parameters for IV calculation
    params = OptionParameters(
        spot_price=spot,
        strike_price=strike,
        time_to_maturity=time_to_maturity,
        volatility=0.8,  # Initial guess
        risk_free_rate=0.05,
        option_type=OptionType.CALL if option_type.lower() == 'call' else OptionType.PUT,
        is_coin_based=True
    )
    
    # Calculate implied volatility
    iv = bs_model.calculate_implied_volatility(deribit_price_btc, params)
    
    # Calculate theoretical price with this IV
    params.volatility = iv
    theoretical = bs_model.calculate_option_price(params)
    
    return {
        'implied_volatility': iv,
        'deribit_price_btc': deribit_price_btc,
        'theoretical_price_btc': theoretical.coin_based_price,
        'theoretical_price_usd': theoretical.usd_price,
        'price_difference_btc': abs(deribit_price_btc - theoretical.coin_based_price),
        'delta': theoretical.delta,
        'gamma': theoretical.gamma
    }


if __name__ == "__main__":
    # Example usage
    print("Black-Scholes Model with Coin-Based Pricing")
    print("=" * 50)
    
    # Example 1: Standard USD-based option
    print("\n1. Standard USD-based BTC Call Option:")
    spot = 50000  # BTC at $50,000
    strike = 52000  # Strike at $52,000
    time_to_maturity = 30/365  # 30 days
    volatility = 0.8  # 80% annualized volatility
    
    bs_model = BlackScholesModel()
    params = OptionParameters(
        spot_price=spot,
        strike_price=strike,
        time_to_maturity=time_to_maturity,
        volatility=volatility,
        option_type=OptionType.CALL,
        is_coin_based=False
    )
    
    result = bs_model.calculate_option_price(params)
    print(f"   USD Price: ${result.usd_price:.2f}")
    print(f"   BTC Equivalent: {result.coin_based_price:.6f} BTC")
    print(f"   Delta: {result.delta:.4f}")
    print(f"   Gamma: {result.gamma:.6f}")
    
    # Example 2: Coin-based option (Deribit style)
    print("\n2. Coin-based BTC Call Option (Deribit style):")
    params.is_coin_based = True
    result = bs_model.calculate_option_price(params)
    print(f"   BTC Price: {result.coin_based_price:.6f} BTC")
    print(f"   USD Equivalent: ${result.usd_price:.2f}")
    print(f"   Delta (coin-based): {result.delta:.6f}")
    print(f"   Gamma (coin-based): {result.gamma:.9f}")
    
    # Example 3: Quick pricing function
    print("\n3. Quick Coin-Based Pricing:")
    prices = price_coin_based_option(spot, strike, time_to_maturity, volatility, 'call')
    print(f"   Coin Price: {prices['coin_price']:.6f} BTC")
    print(f"   USD Price: ${prices['usd_price']:.2f}")
    
    print("\n✅ Black-Scholes implementation ready for Qortfolio V2!")