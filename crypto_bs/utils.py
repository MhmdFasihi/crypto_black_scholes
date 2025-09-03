def breakeven_price(K, premium, option_type):
    """
    Calculate the breakeven underlying price at expiration for USD-denominated premium.

    This simple formula assumes the premium is in the same units as the strike (USD).
    """
    if option_type.lower() == 'call':
        return K + premium
    elif option_type.lower() == 'put':
        return K - premium
    else:
        raise ValueError("Invalid option_type: must be 'call' or 'put'")


def breakeven_price_coin_based(K, premium_coin, option_type):
    """
    Breakeven underlying price for coin-settled options (premium in coin units).

    For coin-based options (e.g., BTC-settled):
    - Call: payoff in coin is max(S - K, 0)/S. Breakeven when (S - K)/S = premium_coin -> S = K / (1 - premium_coin)
    - Put:  payoff in coin is max(K - S, 0)/S. Breakeven when (K - S)/S = premium_coin -> S = K / (1 + premium_coin)

    Args:
        K: Strike price (USD)
        premium_coin: Premium paid in underlying coin units (e.g., BTC)
        option_type: 'call' or 'put'

    Returns:
        Breakeven underlying price S* in USD
    """
    ot = option_type.lower()
    if ot not in ("call", "put"):
        raise ValueError("Invalid option_type: must be 'call' or 'put'")

    if premium_coin < 0:
        raise ValueError("premium_coin must be non-negative")

    if ot == 'call':
        if premium_coin >= 1:
            raise ValueError("For calls, premium_coin must be < 1 for a finite breakeven")
        return K / (1 - premium_coin)
    else:  # put
        return K / (1 + premium_coin)
