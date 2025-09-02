import numpy as np
from scipy.stats import norm

def black_76_call(F, K, T, sigma):
    """
    Black-76 model for European call option on futures.
    Appropriate for coin-settled crypto options.
    """
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return norm.cdf(d1) - (K / F) * norm.cdf(d2)

def black_76_put(F, K, T, sigma):
    """
    Black-76 model for European put option on futures.
    Appropriate for coin-settled crypto options.
    """
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return (K / F) * norm.cdf(-d2) - norm.cdf(-d1)

def price_option(F, K, T, sigma, option_type):
    """
    Price European options using Black-76 model (suitable for coin-settled crypto options).
    F: forward/futures price
    K: strike price
    T: time to expiration (years)
    sigma: volatility
    option_type: 'call' or 'put'
    """
    if option_type.lower() == 'call':
        return black_76_call(F, K, T, sigma)
    elif option_type.lower() == 'put':
        return black_76_put(F, K, T, sigma)
    else:
        raise ValueError("Invalid option_type: must be 'call' or 'put'")