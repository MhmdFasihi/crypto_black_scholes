import sys
import os

# Add the parent directory to sys.path to ensure crypto_bs can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_bs import price_option, delta, gamma, vega, theta, rho, breakeven_price, get_btc_forward_price, get_option_data, get_available_instruments

# Fetch real data from Deribit
try:
    F = get_btc_forward_price()  # Use BTC perpetual as forward price
    print(f"Current BTC forward price: {F:.2f} USD")
    
    # Get available instruments
    instruments = get_available_instruments()
    print(f"Available instruments: {len(instruments)}")
    
    # Use a realistic instrument (e.g., near-the-money call)
    # For expiry 3SEP25 (Sept 3, 2025), strikes around 105k
    instrument = "BTC-3SEP25-105000-C"  # Call option with strike 105k
    K = 105000  # strike price
    T = 1 / 365  # time to expiry in years (1 day from Sept 2 to Sept 3)
    option_type = "call"
    
    # Fetch real option data
    option_data = get_option_data(instrument)
    sigma = option_data['implied_volatility']
    print(f"Fetched data for {instrument}:")
    print(f"  Mark Price: {option_data['mark_price']:.4f}")
    print(f"  Implied Volatility: {sigma:.4f}")
    print(f"  Bid: {option_data['bid_price']:.4f}")
    print(f"  Ask: {option_data['ask_price']:.4f}")
    
    # Price the option using our model
    price = price_option(F, K, T, sigma, option_type)
    print(f"\nOur model {option_type.capitalize()} option price: {price:.4f} BTC")
    
    # Calculate Greeks
    d = delta(F, K, T, sigma, option_type)
    g = gamma(F, K, T, sigma)
    v = vega(F, K, T, sigma)
    t = theta(F, K, T, sigma, option_type)
    r = rho(F, K, T, sigma, option_type)
    
    print(f"Delta: {d:.4f}")
    print(f"Gamma: {g:.4f}")
    print(f"Vega: {v:.4f}")
    print(f"Theta: {t:.4f}")
    print(f"Rho: {r:.4f}")
    
    # Breakeven price
    be = breakeven_price(K, price, option_type)
    print(f"Breakeven price: {be:.4f} USD")
    
    # For put option with same strike
    option_type_put = "put"
    instrument_put = "BTC-3SEP25-105000-P"
    option_data_put = get_option_data(instrument_put)
    price_put = price_option(F, K, T, sigma, option_type_put)
    print(f"\nPut option mark price from Deribit: {option_data_put['mark_price']:.4f}")
    print(f"Our model put option price: {price_put:.4f} BTC")
    
    d_put = delta(F, K, T, sigma, option_type_put)
    print(f"Put Delta: {d_put:.4f}")
    
    be_put = breakeven_price(K, price_put, option_type_put)
    print(f"Put Breakeven price: {be_put:.4f} USD")
    
except Exception as e:
    print(f"Error: {e}")
    print("Falling back to sample data...")
    
    # Fallback to sample data
    F = 109000
    K = 105000
    T = 1 / 365
    sigma = 0.8
    option_type = "call"
    
    price = price_option(F, K, T, sigma, option_type)
    print(f"Sample {option_type.capitalize()} option price: {price:.4f} BTC")