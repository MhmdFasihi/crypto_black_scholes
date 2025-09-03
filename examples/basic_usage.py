import sys
import os

# Add the parent directory to sys.path to ensure crypto_bs can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_bs import (
    # Basic functions
    price_option, delta, gamma, vega, theta, rho, breakeven_price,
    get_btc_forward_price, get_option_data, get_available_instruments,

    # Advanced classes and functions
    BlackScholesModel, Black76Model, OptionParameters, OptionPricing,
    OptionType, PricingModel, GreeksCalculator,
    price_coin_based_option, validate_deribit_pricing,
    calculate_option_greeks, analyze_portfolio_risk,
    breakeven_price_coin_based
)

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

    print("\n" + "="*60)
    print("COMPARISON: Basic vs Advanced Implementation")
    print("="*60)

    # Method 1: Basic Black-76 pricing
    print("\n1. Basic Black-76 Pricing:")
    price_basic = price_option(F, K, T, sigma, option_type)
    print(f"   Price: {price_basic:.6f} BTC")

    # Method 2: Advanced Black-Scholes with coin-based support
    print("\n2. Advanced Black-Scholes (Coin-Based):")
    bs_model = BlackScholesModel()

    params = OptionParameters(
        spot_price=F,
        strike_price=K,
        time_to_maturity=T,
        volatility=sigma,
        risk_free_rate=0.05,  # For comparison, though coin-based typically uses 0
        option_type=OptionType.CALL,
        is_coin_based=True
    )

    result = bs_model.calculate_option_price(params)
    print(f"   Coin Price: {result.coin_based_price:.6f} BTC")
    print(f"   USD Equivalent: ${result.usd_price:.2f}")
    print(f"   Delta: {result.delta:.6f}")
    print(f"   Gamma: {result.gamma:.9f}")
    print(f"   Theta: {result.theta:.9f}")
    print(f"   Vega: {result.vega:.6f}")
    print(f"   Rho: {result.rho:.9f}")

    # Method 3: Quick coin-based pricing function
    print("\n3. Quick Coin-Based Pricing:")
    quick_prices = price_coin_based_option(F, K, T, sigma, 'call')
    print(f"   Coin Price: {quick_prices['coin_price']:.6f} BTC")
    print(f"   USD Price: ${quick_prices['usd_price']:.2f}")

    # Method 4: Advanced Greeks Calculator
    print("\n4. Advanced Greeks Calculator:")
    greeks = calculate_option_greeks(F, K, T, sigma, 'call', is_coin_based=True)
    for name, value in greeks.items():
        if value is not None:
            print(f"   {name.capitalize()}: {value:.6f}")

    # Breakeven calculation
    print("\n5. Breakeven Analysis:")
    be = breakeven_price_coin_based(K, result.coin_based_price, option_type)
    print(f"   Breakeven Price (coin-based): {be:.2f} USD")
    print(f"   Current Distance to Breakeven: {((be - F) / F * 100):.2f}%")

    # Validate against Deribit pricing
    print("\n6. Deribit Validation:")
    validation = validate_deribit_pricing(
        deribit_price_btc=option_data['mark_price'],
        spot=F,
        strike=K,
        time_to_maturity=T,
        option_type='call'
    )
    print(f"   Implied Volatility: {validation['implied_volatility']:.4f}")
    print(f"   Deribit Price: {validation['deribit_price_btc']:.6f} BTC")
    print(f"   Theoretical Price: {validation['theoretical_price_btc']:.6f} BTC")
    print(f"   Price Difference: {validation['price_difference_btc']:.6f} BTC")

    print("\n" + "="*60)
    print("PORTFOLIO RISK ANALYSIS")
    print("="*60)

    # Sample portfolio
    portfolio = [
        {
            'quantity': 10,
            'spot_price': F,
            'strike_price': K,
            'time_to_maturity': T,
            'volatility': sigma,
            'option_type': 'call',
            'underlying': 'BTC',
            'is_coin_based': True
        },
        {
            'quantity': -5,  # Short position
            'spot_price': F,
            'strike_price': K * 0.95,  # Slightly OTM
            'time_to_maturity': T,
            'volatility': sigma,
            'option_type': 'put',
            'underlying': 'BTC',
            'is_coin_based': True
        }
    ]

    risk_analysis = analyze_portfolio_risk(portfolio)

    print("\nPortfolio Summary:")
    for key, value in risk_analysis['portfolio_summary'].items():
        print(f"   {key}: {value:.4f}")

    print("\nRisk Metrics:")
    for key, value in risk_analysis['risk_metrics'].items():
        if value is not None:
            print(f"   {key}: {value:.4f}")

    print("\nGreeks by Underlying:")
    for underlying, greeks in risk_analysis['by_underlying'].items():
        print(f"   {underlying}: Δ={greeks['delta']:.4f}, Γ={greeks['gamma']:.6f}")

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
    print(f"Sample {option_type.capitalize()} option price: {price:.6f} BTC")

print("\n✅ Advanced Crypto Options Package Demo Complete!")
