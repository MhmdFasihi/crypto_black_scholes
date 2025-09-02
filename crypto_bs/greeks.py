import numpy as np
from scipy.stats import norm

def calculate_d1(F, K, T, sigma):
    return (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))

def calculate_d2(F, K, T, sigma):
    d1 = calculate_d1(F, K, T, sigma)
    return d1 - sigma * np.sqrt(T)

def delta(F, K, T, sigma, option_type):
    d1 = calculate_d1(F, K, T, sigma)
    if option_type.lower() == 'call':
        return norm.cdf(d1)
    elif option_type.lower() == 'put':
        return norm.cdf(d1) - 1
    else:
        raise ValueError("Invalid option_type: must be 'call' or 'put'")

def gamma(F, K, T, sigma):
    d1 = calculate_d1(F, K, T, sigma)
    return norm.pdf(d1) / (F * sigma * np.sqrt(T))

def vega(F, K, T, sigma):
    d1 = calculate_d1(F, K, T, sigma)
    return F * np.sqrt(T) * norm.pdf(d1)

def theta(F, K, T, sigma, option_type):
    d1 = calculate_d1(F, K, T, sigma)
    d2 = calculate_d2(F, K, T, sigma)
    if option_type.lower() == 'call':
        return - (F * sigma * norm.pdf(d1)) / (2 * np.sqrt(T))
    elif option_type.lower() == 'put':
        return - (F * sigma * norm.pdf(d1)) / (2 * np.sqrt(T))
    else:
        raise ValueError("Invalid option_type: must be 'call' or 'put'")

def rho(F, K, T, sigma, option_type):
    # For coin-settled options, rho is typically 0 since r=0
    return 0