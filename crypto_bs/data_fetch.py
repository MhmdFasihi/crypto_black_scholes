import requests

DERIBIT_API_BASE = "https://www.deribit.com/api/v2/public/"
REQUEST_TIMEOUT = 10


def get_btc_forward_price() -> float:
    """
    Fetch BTC perpetual price from Deribit as a proxy for forward price.
    Returns the mark price in USD.
    """
    url = f"{DERIBIT_API_BASE}ticker?instrument_name=BTC-PERPETUAL"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if data['result']:
        return data['result']['mark_price']
    raise ValueError("Failed to fetch BTC price from Deribit")


def get_option_data(instrument_name: str) -> dict:
    """
    Fetch option data from Deribit for a specific instrument.
    instrument_name example: 'BTC-30SEP25-40000-C' for call option.
    Returns a dict with price, implied_volatility, etc.
    """
    url = f"{DERIBIT_API_BASE}ticker?instrument_name={instrument_name}"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if data['result']:
        result = data['result']
        return {
            'mark_price': result['mark_price'],
            'implied_volatility': result['mark_iv'] / 100,
            'bid_price': result['best_bid_price'],
            'ask_price': result['best_ask_price'],
            'underlying_price': result['underlying_price']
        }
    raise ValueError(f"Failed to fetch data for {instrument_name}")


def get_available_instruments(currency: str = 'BTC', kind: str = 'option') -> list:
    """Fetch list of available option instruments."""
    url = f"{DERIBIT_API_BASE}get_instruments?currency={currency}&kind={kind}&expired=false"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if data['result']:
        return [inst['instrument_name'] for inst in data['result']]
    raise ValueError("Failed to fetch instruments")


def get_btc_price() -> float:
    """Fetch current BTC price in USD from CoinGecko."""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    return data['bitcoin']['usd']


def get_btc_volatility() -> float:
    """
    Historical / realized volatility from market data is not implemented in this release.

    Raises:
        NotImplementedError: Always, until a dedicated historical_vol module ships.
    """
    raise NotImplementedError(
        "get_btc_volatility is not implemented. Use your own realized vol from returns "
        "or an external data source; a historical_vol helper is planned for a future release."
    )
