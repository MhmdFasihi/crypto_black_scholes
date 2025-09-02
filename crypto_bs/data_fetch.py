import requests
import json

DERIBIT_API_BASE = "https://www.deribit.com/api/v2/public/"

def get_btc_forward_price():
    """
    Fetch BTC perpetual price from Deribit as a proxy for forward price.
    Returns the mark price in USD.
    """
    url = f"{DERIBIT_API_BASE}ticker?instrument_name=BTC-PERPETUAL"
    response = requests.get(url)
    data = response.json()
    if data['result']:
        return data['result']['mark_price']
    else:
        raise ValueError("Failed to fetch BTC price from Deribit")

def get_option_data(instrument_name):
    """
    Fetch option data from Deribit for a specific instrument.
    instrument_name example: 'BTC-30SEP25-40000-C' for call option.
    Returns a dict with price, implied_volatility, etc.
    """
    url = f"{DERIBIT_API_BASE}ticker?instrument_name={instrument_name}"
    response = requests.get(url)
    data = response.json()
    if data['result']:
        result = data['result']
        return {
            'mark_price': result['mark_price'],
            'implied_volatility': result['mark_iv'] / 100,  # Deribit returns IV as percentage
            'bid_price': result['best_bid_price'],
            'ask_price': result['best_ask_price'],
            'underlying_price': result['underlying_price']
        }
    else:
        raise ValueError(f"Failed to fetch data for {instrument_name}")

def get_available_instruments(currency='BTC', kind='option'):
    """
    Fetch list of available option instruments for BTC.
    """
    url = f"{DERIBIT_API_BASE}get_instruments?currency={currency}&kind={kind}&expired=false"
    response = requests.get(url)
    data = response.json()
    if data['result']:
        return [inst['instrument_name'] for inst in data['result']]
    else:
        raise ValueError("Failed to fetch instruments")

# Keep the old function for backward compatibility or general use
def get_btc_price():
    """
    Fetch current BTC price from CoinGecko API.
    Returns the price in USD.
    """
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    response = requests.get(url)
    data = response.json()
    return data['bitcoin']['usd']

def get_btc_volatility():
    """
    Placeholder for volatility calculation.
    In a real implementation, this would fetch historical data and calculate implied volatility.
    For now, returns a sample value.
    """
    # This is a placeholder - real implementation would require historical data
    return 0.5  # Sample volatility