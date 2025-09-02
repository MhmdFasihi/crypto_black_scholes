def breakeven_price(K, premium, option_type):
    """
    Calculate the breakeven price for the option at expiration.
    For coin-settled options, premium is in the same units as the underlying.
    """
    if option_type.lower() == 'call':
        return K + premium
    elif option_type.lower() == 'put':
        return K - premium
    else:
        raise ValueError("Invalid option_type: must be 'call' or 'put'")