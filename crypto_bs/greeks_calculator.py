# Copyright (c) 2025 Seyed Mohammad Hossein Fasihi (Mhmd Fasihi)
# This file is part of a project licensed under AGPLv3 or a commercial license.
# AGPLv3: https://www.gnu.org/licenses/agpl-3.0.html
# Contact for commercial licensing: mhmd.fasihi@gmail.com

"""
Greeks Calculator Module with Portfolio-Level Analysis
Supports coin-based options and portfolio risk metrics
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta

# Import the Black-Scholes model
from .black_scholes import BlackScholesModel, OptionParameters, OptionType, OptionPricing

logger = logging.getLogger(__name__)


@dataclass
class GreeksProfile:
    """Complete Greeks profile for an option or portfolio."""
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    speed: Optional[float] = None  # Gamma derivative
    charm: Optional[float] = None  # Delta decay
    vanna: Optional[float] = None  # Delta/Vega cross
    vomma: Optional[float] = None  # Vega derivative
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'delta': self.delta,
            'gamma': self.gamma,
            'theta': self.theta,
            'vega': self.vega,
            'rho': self.rho,
            'speed': self.speed,
            'charm': self.charm,
            'vanna': self.vanna,
            'vomma': self.vomma
        }


@dataclass
class PortfolioGreeks:
    """Portfolio-level Greeks aggregation."""
    total_delta: float
    total_gamma: float
    total_theta: float
    total_vega: float
    total_rho: float
    portfolio_value: float
    delta_dollars: float  # Dollar delta exposure
    gamma_dollars: float  # Dollar gamma exposure
    positions_count: int
    by_underlying: Dict[str, GreeksProfile] = field(default_factory=dict)
    by_expiry: Dict[str, GreeksProfile] = field(default_factory=dict)
    
    def get_summary(self) -> Dict[str, float]:
        """Get portfolio summary."""
        return {
            'portfolio_value': self.portfolio_value,
            'total_delta': self.total_delta,
            'total_gamma': self.total_gamma,
            'total_theta': self.total_theta,
            'total_vega': self.total_vega,
            'total_rho': self.total_rho,
            'delta_dollars': self.delta_dollars,
            'gamma_dollars': self.gamma_dollars,
            'positions_count': self.positions_count
        }


@dataclass
class RiskMetrics:
    """Risk metrics for options portfolio."""
    gamma_exposure: float  # Total gamma exposure in dollars
    gamma_flip_point: Optional[float]  # Price where gamma changes sign
    max_gamma_strike: float  # Strike with maximum gamma
    pin_risk: float  # Risk near expiration
    vega_exposure: float  # Total vega exposure
    theta_decay_daily: float  # Daily theta decay
    delta_neutral_hedge: float  # Shares needed for delta neutrality


class GreeksCalculator:
    """
    Advanced Greeks calculator with portfolio support.
    Handles both standard and coin-based options.
    """
    
    def __init__(self, bs_model: Optional[BlackScholesModel] = None):
        """
        Initialize Greeks calculator.
        
        Args:
            bs_model: Black-Scholes model instance (creates new if None)
        """
        self.bs_model = bs_model or BlackScholesModel()
        self.logger = logging.getLogger(__name__)
    
    def calculate_option_greeks(self, params: OptionParameters) -> GreeksProfile:
        """
        Calculate all Greeks for a single option.
        
        Args:
            params: Option parameters
            
        Returns:
            Complete Greeks profile
        """
        # Get first-order Greeks from Black-Scholes
        pricing = self.bs_model.calculate_option_price(params)
        
        # Calculate second-order Greeks if needed
        second_order = self._calculate_second_order_greeks(params) if params.time_to_maturity > 0 else {}
        
        return GreeksProfile(
            delta=pricing.delta,
            gamma=pricing.gamma,
            theta=pricing.theta,
            vega=pricing.vega,
            rho=pricing.rho,
            speed=second_order.get('speed'),
            charm=second_order.get('charm'),
            vanna=second_order.get('vanna'),
            vomma=second_order.get('vomma')
        )
    
    def _calculate_second_order_greeks(self, params: OptionParameters) -> Dict[str, float]:
        """
        Calculate second-order Greeks using finite differences.
        
        Args:
            params: Option parameters
            
        Returns:
            Dictionary of second-order Greeks
        """
        eps_price = params.spot_price * 0.001  # 0.1% bump
        eps_vol = 0.001  # 0.1% vol bump
        eps_time = 1/365  # 1 day bump
        
        second_order = {}
        
        try:
            # Speed: Rate of change of Gamma with respect to spot
            params_up = OptionParameters(**{**params.__dict__, 'spot_price': params.spot_price + eps_price})
            params_down = OptionParameters(**{**params.__dict__, 'spot_price': params.spot_price - eps_price})
            
            gamma_up = self.bs_model.calculate_option_price(params_up).gamma
            gamma_down = self.bs_model.calculate_option_price(params_down).gamma
            second_order['speed'] = (gamma_up - gamma_down) / (2 * eps_price)
            
            # Charm: Rate of change of Delta with respect to time
            if params.time_to_maturity > eps_time:
                params_later = OptionParameters(**{**params.__dict__, 
                                               'time_to_maturity': params.time_to_maturity - eps_time})
                delta_later = self.bs_model.calculate_option_price(params_later).delta
                delta_now = self.bs_model.calculate_option_price(params).delta
                second_order['charm'] = -(delta_later - delta_now) / eps_time
            
            # Vanna: Cross-derivative of Delta with respect to volatility
            params_vol_up = OptionParameters(**{**params.__dict__, 
                                            'volatility': params.volatility + eps_vol})
            delta_vol_up = self.bs_model.calculate_option_price(params_vol_up).delta
            delta_base = self.bs_model.calculate_option_price(params).delta
            second_order['vanna'] = (delta_vol_up - delta_base) / eps_vol
            
            # Vomma: Rate of change of Vega with respect to volatility
            vega_vol_up = self.bs_model.calculate_option_price(params_vol_up).vega
            vega_base = self.bs_model.calculate_option_price(params).vega
            second_order['vomma'] = (vega_vol_up - vega_base) / eps_vol
            
        except Exception as e:
            self.logger.warning(f"Could not calculate second-order Greeks: {e}")
        
        return second_order
    
    def calculate_portfolio_greeks(self, positions: List[Dict]) -> PortfolioGreeks:
        """
        Calculate portfolio-level Greeks.
        
        Args:
            positions: List of position dictionaries with keys:
                - quantity: Position size (positive for long, negative for short)
                - spot_price: Current spot price
                - strike_price: Strike price
                - time_to_maturity: Time to maturity in years
                - volatility: Implied volatility
                - option_type: 'call' or 'put'
                - underlying: Underlying asset symbol (e.g., 'BTC', 'ETH')
                - is_coin_based: Whether option is coin-based
                
        Returns:
            Portfolio-level Greeks
        """
        total_delta = 0
        total_gamma = 0
        total_theta = 0
        total_vega = 0
        total_rho = 0
        portfolio_value = 0
        
        by_underlying = {}
        by_expiry = {}
        
        for position in positions:
            # Create option parameters
            params = OptionParameters(
                spot_price=position['spot_price'],
                strike_price=position['strike_price'],
                time_to_maturity=position['time_to_maturity'],
                volatility=position['volatility'],
                risk_free_rate=position.get('risk_free_rate', 0.05),
                option_type=OptionType.CALL if position['option_type'].lower() == 'call' else OptionType.PUT,
                is_coin_based=position.get('is_coin_based', False)
            )
            
            # Calculate Greeks for this position
            pricing = self.bs_model.calculate_option_price(params)
            quantity = position['quantity']
            
            # Aggregate Greeks
            total_delta += pricing.delta * quantity
            total_gamma += pricing.gamma * quantity
            total_theta += pricing.theta * quantity
            total_vega += pricing.vega * quantity
            total_rho += pricing.rho * quantity
            
            # Calculate position value
            if params.is_coin_based:
                position_value = pricing.coin_based_price * quantity * position['spot_price']
            else:
                position_value = pricing.usd_price * quantity
            portfolio_value += position_value
            
            # Aggregate by underlying
            underlying = position.get('underlying', 'UNKNOWN')
            if underlying not in by_underlying:
                by_underlying[underlying] = {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'rho': 0}
            by_underlying[underlying]['delta'] += pricing.delta * quantity
            by_underlying[underlying]['gamma'] += pricing.gamma * quantity
            by_underlying[underlying]['theta'] += pricing.theta * quantity
            by_underlying[underlying]['vega'] += pricing.vega * quantity
            by_underlying[underlying]['rho'] += pricing.rho * quantity
            
            # Aggregate by expiry
            expiry_key = f"{int(position['time_to_maturity'] * 365)}d"
            if expiry_key not in by_expiry:
                by_expiry[expiry_key] = {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'rho': 0}
            by_expiry[expiry_key]['delta'] += pricing.delta * quantity
            by_expiry[expiry_key]['gamma'] += pricing.gamma * quantity
            by_expiry[expiry_key]['theta'] += pricing.theta * quantity
            by_expiry[expiry_key]['vega'] += pricing.vega * quantity
            by_expiry[expiry_key]['rho'] += pricing.rho * quantity
        
        # Calculate dollar exposures (assuming average spot price)
        avg_spot = np.mean([p['spot_price'] for p in positions]) if positions else 0
        delta_dollars = total_delta * avg_spot
        gamma_dollars = total_gamma * avg_spot * avg_spot / 100  # Per 1% move
        
        # Convert aggregated dicts to GreeksProfile objects
        by_underlying_profiles = {
            k: GreeksProfile(
                delta=v['delta'], gamma=v['gamma'], theta=v['theta'],
                vega=v['vega'], rho=v['rho']
            ) for k, v in by_underlying.items()
        }
        
        by_expiry_profiles = {
            k: GreeksProfile(
                delta=v['delta'], gamma=v['gamma'], theta=v['theta'],
                vega=v['vega'], rho=v['rho']
            ) for k, v in by_expiry.items()
        }
        
        return PortfolioGreeks(
            total_delta=total_delta,
            total_gamma=total_gamma,
            total_theta=total_theta,
            total_vega=total_vega,
            total_rho=total_rho,
            portfolio_value=portfolio_value,
            delta_dollars=delta_dollars,
            gamma_dollars=gamma_dollars,
            positions_count=len(positions),
            by_underlying=by_underlying_profiles,
            by_expiry=by_expiry_profiles
        )
    
    def calculate_risk_metrics(self, positions: List[Dict]) -> RiskMetrics:
        """
        Calculate advanced risk metrics for portfolio.
        
        Args:
            positions: List of position dictionaries
            
        Returns:
            Risk metrics
        """
        portfolio_greeks = self.calculate_portfolio_greeks(positions)
        
        # Calculate gamma exposure
        avg_spot = np.mean([p['spot_price'] for p in positions]) if positions else 0
        gamma_exposure = portfolio_greeks.total_gamma * avg_spot * avg_spot / 100
        
        # Find maximum gamma strike
        gamma_by_strike = {}
        for position in positions:
            strike = position['strike_price']
            params = OptionParameters(
                spot_price=position['spot_price'],
                strike_price=strike,
                time_to_maturity=position['time_to_maturity'],
                volatility=position['volatility'],
                option_type=OptionType.CALL if position['option_type'].lower() == 'call' else OptionType.PUT,
                is_coin_based=position.get('is_coin_based', False)
            )
            pricing = self.bs_model.calculate_option_price(params)
            gamma_by_strike[strike] = gamma_by_strike.get(strike, 0) + pricing.gamma * position['quantity']
        
        max_gamma_strike = max(gamma_by_strike.keys(), key=lambda k: abs(gamma_by_strike[k])) if gamma_by_strike else 0
        
        # Calculate pin risk (gamma near expiration)
        short_dated_gamma = sum(
            self.bs_model.calculate_option_price(
                OptionParameters(
                    spot_price=p['spot_price'],
                    strike_price=p['strike_price'],
                    time_to_maturity=p['time_to_maturity'],
                    volatility=p['volatility'],
                    option_type=OptionType.CALL if p['option_type'].lower() == 'call' else OptionType.PUT,
                    is_coin_based=p.get('is_coin_based', False)
                )
            ).gamma * p['quantity']
            for p in positions if p['time_to_maturity'] < 7/365  # Less than 7 days
        )
        pin_risk = abs(short_dated_gamma * avg_spot * avg_spot * 0.01)  # 1% move impact
        
        # Calculate gamma flip point (simplified)
        gamma_flip_point = None
        if portfolio_greeks.total_gamma != 0:
            # Approximate where gamma changes sign
            test_prices = np.linspace(avg_spot * 0.8, avg_spot * 1.2, 20)
            gamma_signs = []
            for test_price in test_prices:
                test_gamma = 0
                for position in positions:
                    params = OptionParameters(
                        spot_price=test_price,
                        strike_price=position['strike_price'],
                        time_to_maturity=position['time_to_maturity'],
                        volatility=position['volatility'],
                        option_type=OptionType.CALL if position['option_type'].lower() == 'call' else OptionType.PUT,
                        is_coin_based=position.get('is_coin_based', False)
                    )
                    test_gamma += self.bs_model.calculate_option_price(params).gamma * position['quantity']
                gamma_signs.append((test_price, test_gamma))
            
            # Find sign change
            for i in range(1, len(gamma_signs)):
                if gamma_signs[i-1][1] * gamma_signs[i][1] < 0:
                    gamma_flip_point = (gamma_signs[i-1][0] + gamma_signs[i][0]) / 2
                    break
        
        return RiskMetrics(
            gamma_exposure=gamma_exposure,
            gamma_flip_point=gamma_flip_point,
            max_gamma_strike=max_gamma_strike,
            pin_risk=pin_risk,
            vega_exposure=portfolio_greeks.total_vega,
            theta_decay_daily=portfolio_greeks.total_theta,
            delta_neutral_hedge=-portfolio_greeks.total_delta
        )
    
    def calculate_gamma_exposure_profile(self, positions: List[Dict], 
                                        price_range: Tuple[float, float] = (0.8, 1.2),
                                        steps: int = 50) -> pd.DataFrame:
        """
        Calculate gamma exposure across price range.
        
        Args:
            positions: List of position dictionaries
            price_range: Range as multipliers of current spot (e.g., (0.8, 1.2))
            steps: Number of price points to calculate
            
        Returns:
            DataFrame with price and gamma exposure
        """
        results = []
        
        # Get average spot price
        avg_spot = np.mean([p['spot_price'] for p in positions]) if positions else 100
        
        # Generate price points
        prices = np.linspace(avg_spot * price_range[0], avg_spot * price_range[1], steps)
        
        for price in prices:
            total_gamma = 0
            for position in positions:
                params = OptionParameters(
                    spot_price=price,
                    strike_price=position['strike_price'],
                    time_to_maturity=position['time_to_maturity'],
                    volatility=position['volatility'],
                    option_type=OptionType.CALL if position['option_type'].lower() == 'call' else OptionType.PUT,
                    is_coin_based=position.get('is_coin_based', False)
                )
                pricing = self.bs_model.calculate_option_price(params)
                total_gamma += pricing.gamma * position['quantity']
            
            gamma_exposure = total_gamma * price * price / 100  # Dollar gamma per 1% move
            
            results.append({
                'price': price,
                'gamma': total_gamma,
                'gamma_exposure': gamma_exposure,
                'price_pct_from_spot': (price / avg_spot - 1) * 100
            })
        
        return pd.DataFrame(results)


# Convenience functions
def calculate_option_greeks(spot: float, strike: float, time_to_maturity: float,
                           volatility: float, option_type: str = 'call',
                           is_coin_based: bool = False) -> Dict[str, float]:
    """
    Quick Greeks calculation for a single option.
    
    Returns dictionary with all Greeks.
    """
    calc = GreeksCalculator()
    params = OptionParameters(
        spot_price=spot,
        strike_price=strike,
        time_to_maturity=time_to_maturity,
        volatility=volatility,
        option_type=OptionType.CALL if option_type.lower() == 'call' else OptionType.PUT,
        is_coin_based=is_coin_based
    )
    
    greeks = calc.calculate_option_greeks(params)
    return greeks.to_dict()


def analyze_portfolio_risk(positions: List[Dict]) -> Dict[str, any]:
    """
    Analyze portfolio risk metrics.
    
    Args:
        positions: List of position dictionaries
        
    Returns:
        Dictionary with portfolio Greeks and risk metrics
    """
    calc = GreeksCalculator()
    
    portfolio_greeks = calc.calculate_portfolio_greeks(positions)
    risk_metrics = calc.calculate_risk_metrics(positions)
    
    return {
        'portfolio_summary': portfolio_greeks.get_summary(),
        'risk_metrics': {
            'gamma_exposure': risk_metrics.gamma_exposure,
            'gamma_flip_point': risk_metrics.gamma_flip_point,
            'max_gamma_strike': risk_metrics.max_gamma_strike,
            'pin_risk': risk_metrics.pin_risk,
            'vega_exposure': risk_metrics.vega_exposure,
            'theta_decay_daily': risk_metrics.theta_decay_daily,
            'delta_neutral_hedge': risk_metrics.delta_neutral_hedge
        },
        'by_underlying': {k: v.to_dict() for k, v in portfolio_greeks.by_underlying.items()},
        'by_expiry': {k: v.to_dict() for k, v in portfolio_greeks.by_expiry.items()}
    }


if __name__ == "__main__":
    # Example usage
    print("Greeks Calculator with Portfolio Support")
    print("=" * 50)
    
    # Example 1: Single option Greeks
    print("\n1. Single BTC Call Option Greeks:")
    greeks = calculate_option_greeks(
        spot=50000,
        strike=52000,
        time_to_maturity=30/365,
        volatility=0.8,
        option_type='call',
        is_coin_based=True
    )
    
    for name, value in greeks.items():
        if value is not None:
            print(f"   {name}: {value:.6f}")
    
    # Example 2: Portfolio Greeks
    print("\n2. Portfolio Greeks Analysis:")
    
    # Sample portfolio
    portfolio = [
        {
            'quantity': 10,
            'spot_price': 50000,
            'strike_price': 52000,
            'time_to_maturity': 30/365,
            'volatility': 0.8,
            'option_type': 'call',
            'underlying': 'BTC',
            'is_coin_based': True
        },
        {
            'quantity': -5,  # Short position
            'spot_price': 50000,
            'strike_price': 48000,
            'time_to_maturity': 15/365,
            'volatility': 0.75,
            'option_type': 'put',
            'underlying': 'BTC',
            'is_coin_based': True
        },
        {
            'quantity': 20,
            'spot_price': 3500,
            'strike_price': 3600,
            'time_to_maturity': 45/365,
            'volatility': 0.85,
            'option_type': 'call',
            'underlying': 'ETH',
            'is_coin_based': True
        }
    ]
    
    risk_analysis = analyze_portfolio_risk(portfolio)
    
    print("\n   Portfolio Summary:")
    for key, value in risk_analysis['portfolio_summary'].items():
        print(f"      {key}: {value:.4f}")
    
    print("\n   Risk Metrics:")
    for key, value in risk_analysis['risk_metrics'].items():
        if value is not None:
            print(f"      {key}: {value:.4f}")
    
    print("\n   Greeks by Underlying:")
    for underlying, greeks in risk_analysis['by_underlying'].items():
        print(f"      {underlying}: Δ={greeks['delta']:.4f}, Γ={greeks['gamma']:.6f}")
    
    print("\n✅ Greeks Calculator ready for Qortfolio V2!")