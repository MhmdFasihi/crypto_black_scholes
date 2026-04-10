"""Market-data helpers for Deribit and BTC spot/volatility inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any
import time

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .historical_vol import close_to_close_hv


DERIBIT_API_BASE = "https://www.deribit.com/api/v2/public/"
COINGECKO_API_BASE = "https://api.coingecko.com/api/v3/"
REQUEST_TIMEOUT = 10
DEFAULT_RATE_LIMIT = 20.0
DEFAULT_CACHE_TTL = 5.0


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_float(value: Any, *, field_name: str) -> float:
    if value is None:
        raise ValueError(f"Missing required numeric field: {field_name}")
    return float(value)


def _maybe_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _expiry_from_timestamp(expiration_timestamp: Any, instrument_name: str) -> datetime:
    if expiration_timestamp is None:
        raise ValueError(f"Missing expiration timestamp for {instrument_name}")
    return datetime.fromtimestamp(float(expiration_timestamp) / 1000.0, tz=timezone.utc)


@dataclass
class DeribitClient:
    """
    Reusable client for Deribit public endpoints and BTC spot/vol inputs.

    Features:
    - request retries for transient HTTP failures
    - lightweight pacing against Deribit public rate limits
    - short-lived in-memory response cache for repeated calls
    """

    timeout: int = REQUEST_TIMEOUT
    max_retries: int = 3
    backoff_factor: float = 0.3
    rate_limit_per_second: float = DEFAULT_RATE_LIMIT
    default_cache_ttl: float = DEFAULT_CACHE_TTL
    session: requests.Session | None = None
    _cache: dict[tuple[str, str, tuple[tuple[str, Any], ...]], tuple[float, Any]] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _last_request_time: float = field(default=0.0, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()
            retry = Retry(
                total=self.max_retries,
                connect=self.max_retries,
                read=self.max_retries,
                backoff_factor=self.backoff_factor,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset({"GET"}),
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)
        self.session.headers.setdefault("User-Agent", "crypto_bs/0.6.0")

    def close(self) -> None:
        """Close the underlying HTTP session."""
        if self.session is not None:
            self.session.close()

    def _rate_limit(self) -> None:
        if self.rate_limit_per_second <= 0:
            return
        min_interval = 1.0 / self.rate_limit_per_second
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            self._last_request_time = time.monotonic()

    def _request_json(
        self,
        *,
        base_url: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        cache_ttl: float | None = None,
    ) -> dict[str, Any]:
        normalized_params = tuple(sorted((params or {}).items()))
        cache_seconds = self.default_cache_ttl if cache_ttl is None else cache_ttl
        cache_key = (base_url, endpoint, normalized_params)
        if cache_seconds > 0:
            cached = self._cache.get(cache_key)
            if cached and cached[0] >= time.monotonic():
                return cached[1]

        self._rate_limit()
        response = self.session.get(  # type: ignore[union-attr]
            f"{base_url}{endpoint}",
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, dict) and payload.get("error"):
            raise ValueError(f"API error from {endpoint}: {payload['error']}")

        if cache_seconds > 0:
            self._cache[cache_key] = (time.monotonic() + cache_seconds, payload)
        return payload

    def _deribit_get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        cache_ttl: float | None = None,
    ) -> dict[str, Any]:
        return self._request_json(
            base_url=DERIBIT_API_BASE,
            endpoint=endpoint,
            params=params,
            cache_ttl=cache_ttl,
        )

    def _coingecko_get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        cache_ttl: float | None = None,
    ) -> dict[str, Any]:
        return self._request_json(
            base_url=COINGECKO_API_BASE,
            endpoint=endpoint,
            params=params,
            cache_ttl=cache_ttl,
        )

    def get_instruments(
        self,
        currency: str = "BTC",
        kind: str = "option",
        expired: bool = False,
        cache_ttl: float = 30.0,
    ) -> list[dict[str, Any]]:
        """Return Deribit instrument metadata for the requested product set."""
        payload = self._deribit_get(
            "get_instruments",
            {
                "currency": currency,
                "kind": kind,
                "expired": str(expired).lower(),
            },
            cache_ttl=cache_ttl,
        )
        result = payload.get("result")
        if not isinstance(result, list):
            raise ValueError("Failed to fetch instruments")
        return result

    def get_available_instruments(
        self,
        currency: str = "BTC",
        kind: str = "option",
        expired: bool = False,
        cache_ttl: float = 30.0,
    ) -> list[str]:
        """Return available Deribit instrument names."""
        instruments = self.get_instruments(
            currency=currency,
            kind=kind,
            expired=expired,
            cache_ttl=cache_ttl,
        )
        return [str(inst["instrument_name"]) for inst in instruments]

    def get_ticker(self, instrument_name: str, cache_ttl: float = 1.0) -> dict[str, Any]:
        """Fetch ticker payload for a specific Deribit instrument."""
        payload = self._deribit_get(
            "ticker",
            {"instrument_name": instrument_name},
            cache_ttl=cache_ttl,
        )
        result = payload.get("result")
        if not isinstance(result, dict):
            raise ValueError(f"Failed to fetch ticker for {instrument_name}")
        return result

    def get_btc_forward_price(self) -> float:
        """
        Fetch BTC perpetual mark price from Deribit as a liquid forward proxy.
        Returns the mark price in USD.
        """
        ticker = self.get_ticker("BTC-PERPETUAL")
        return _coerce_float(ticker.get("mark_price"), field_name="mark_price")

    def get_option_data(self, instrument_name: str) -> dict[str, float | str | None]:
        """
        Fetch option data for a Deribit instrument.

        Returns normalized keys including mark price, IV, bid/ask, and underlying.
        """
        result = self.get_ticker(instrument_name)
        mark_iv = _maybe_float(result.get("mark_iv"))
        return {
            "instrument_name": instrument_name,
            "mark_price": _coerce_float(result.get("mark_price"), field_name="mark_price"),
            "implied_volatility": None if mark_iv is None else mark_iv / 100.0,
            "bid_price": _maybe_float(result.get("best_bid_price")),
            "ask_price": _maybe_float(result.get("best_ask_price")),
            "underlying_price": _maybe_float(result.get("underlying_price")),
            "open_interest": _maybe_float(result.get("open_interest")),
        }

    def get_btc_price(self, cache_ttl: float = 10.0) -> float:
        """Fetch current BTC spot price in USD from CoinGecko."""
        payload = self._coingecko_get(
            "simple/price",
            {"ids": "bitcoin", "vs_currencies": "usd"},
            cache_ttl=cache_ttl,
        )
        try:
            return float(payload["bitcoin"]["usd"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Failed to fetch BTC price from CoinGecko") from exc

    def get_historical_prices(
        self,
        *,
        coin_id: str = "bitcoin",
        vs_currency: str = "usd",
        days: int = 90,
        interval: str = "daily",
        cache_ttl: float = 300.0,
    ) -> pd.Series:
        """Fetch historical spot prices from CoinGecko as a UTC-indexed series."""
        if days < 2:
            raise ValueError("days must be >= 2")
        payload = self._coingecko_get(
            f"coins/{coin_id}/market_chart",
            {
                "vs_currency": vs_currency,
                "days": days,
                "interval": interval,
            },
            cache_ttl=cache_ttl,
        )
        prices = payload.get("prices")
        if not isinstance(prices, list) or not prices:
            raise ValueError("Historical price response did not contain prices")
        index = [
            datetime.fromtimestamp(float(timestamp) / 1000.0, tz=timezone.utc)
            for timestamp, _ in prices
        ]
        values = [float(price) for _, price in prices]
        return pd.Series(values, index=pd.DatetimeIndex(index, tz="UTC"), name=f"{coin_id}_{vs_currency}")

    def get_btc_volatility(
        self,
        *,
        days: int = 90,
        window: int = 30,
        trading_days: int = 365,
    ) -> float:
        """
        Estimate BTC realized volatility from historical daily closes.

        The result is annualized using the supplied ``trading_days`` convention.
        """
        prices = self.get_historical_prices(days=days)
        hv = close_to_close_hv(prices, window=window, trading_days=trading_days).dropna()
        if hv.empty:
            raise ValueError(
                f"Not enough historical prices to compute volatility with window={window}"
            )
        return float(hv.iloc[-1])

    def get_full_chain(
        self,
        *,
        currency: str = "BTC",
        kind: str = "option",
        expired: bool = False,
        min_open_interest: float = 0.0,
        as_of: datetime | None = None,
        cache_ttl: float = 3.0,
    ) -> pd.DataFrame:
        """
        Fetch and normalize a full Deribit options chain.

        Returns a dataframe with instrument metadata, prices, IV, OI, and
        time-to-maturity in years.
        """
        columns = [
            "instrument_name",
            "currency",
            "strike",
            "option_type",
            "expiry",
            "time_to_maturity",
            "underlying_price",
            "mark_price",
            "mid_price",
            "bid_price",
            "ask_price",
            "implied_volatility",
            "open_interest",
            "volume",
        ]
        instruments = self.get_instruments(
            currency=currency,
            kind=kind,
            expired=expired,
            cache_ttl=max(cache_ttl, 30.0),
        )
        summary_payload = self._deribit_get(
            "get_book_summary_by_currency",
            {"currency": currency, "kind": kind},
            cache_ttl=cache_ttl,
        )
        summaries = summary_payload.get("result")
        if not isinstance(summaries, list):
            raise ValueError("Failed to fetch Deribit chain summary")

        summary_map = {
            str(item["instrument_name"]): item
            for item in summaries
            if isinstance(item, dict) and "instrument_name" in item
        }
        now = _utc_now() if as_of is None else as_of.astimezone(timezone.utc)

        rows: list[dict[str, Any]] = []
        for inst in instruments:
            instrument_name = str(inst["instrument_name"])
            summary = summary_map.get(instrument_name)
            if summary is None:
                continue

            open_interest = float(summary.get("open_interest") or 0.0)
            if open_interest < min_open_interest:
                continue

            expiry = _expiry_from_timestamp(inst.get("expiration_timestamp"), instrument_name)
            bid_price = _maybe_float(summary.get("bid_price"))
            ask_price = _maybe_float(summary.get("ask_price"))
            mark_price = _maybe_float(summary.get("mark_price"))
            if bid_price is not None and ask_price is not None:
                mid_price = 0.5 * (bid_price + ask_price)
            else:
                mid_price = mark_price

            mark_iv = _maybe_float(summary.get("mark_iv"))
            rows.append(
                {
                    "instrument_name": instrument_name,
                    "currency": str(inst.get("base_currency", currency)),
                    "strike": _coerce_float(inst.get("strike"), field_name="strike"),
                    "option_type": str(inst.get("option_type", "")).lower(),
                    "expiry": expiry,
                    "time_to_maturity": max((expiry - now).total_seconds(), 0.0)
                    / (365.0 * 24.0 * 3600.0),
                    "underlying_price": _maybe_float(summary.get("underlying_price")),
                    "mark_price": mark_price,
                    "mid_price": mid_price,
                    "bid_price": bid_price,
                    "ask_price": ask_price,
                    "implied_volatility": None if mark_iv is None else mark_iv / 100.0,
                    "open_interest": open_interest,
                    "volume": float(summary.get("volume") or 0.0),
                }
            )

        if not rows:
            return pd.DataFrame(columns=columns)
        return pd.DataFrame(rows, columns=columns).sort_values(
            ["expiry", "strike", "option_type"]
        ).reset_index(drop=True)

    def get_iv_surface_data(
        self,
        *,
        currency: str = "BTC",
        min_open_interest: float = 0.0,
        as_of: datetime | None = None,
        cache_ttl: float = 3.0,
    ) -> pd.DataFrame:
        """
        Fetch the subset of chain fields typically used to fit an IV surface.
        """
        chain = self.get_full_chain(
            currency=currency,
            kind="option",
            expired=False,
            min_open_interest=min_open_interest,
            as_of=as_of,
            cache_ttl=cache_ttl,
        )
        if chain.empty:
            return chain
        surface = chain[
            [
                "instrument_name",
                "expiry",
                "strike",
                "time_to_maturity",
                "option_type",
                "underlying_price",
                "mark_price",
                "mid_price",
                "implied_volatility",
                "open_interest",
            ]
        ].copy()
        surface = surface.dropna(subset=["implied_volatility", "underlying_price"])
        surface = surface[surface["implied_volatility"] > 0].reset_index(drop=True)
        return surface


_DEFAULT_CLIENT: DeribitClient | None = None


def _get_default_client() -> DeribitClient:
    global _DEFAULT_CLIENT
    if _DEFAULT_CLIENT is None:
        _DEFAULT_CLIENT = DeribitClient()
    return _DEFAULT_CLIENT


def get_btc_forward_price() -> float:
    """Fetch BTC perpetual mark price from Deribit as a proxy for forward price."""
    return _get_default_client().get_btc_forward_price()


def get_option_data(instrument_name: str) -> dict[str, float | str | None]:
    """Fetch option data from Deribit for a specific instrument."""
    return _get_default_client().get_option_data(instrument_name)


def get_available_instruments(
    currency: str = "BTC",
    kind: str = "option",
    expired: bool = False,
) -> list[str]:
    """Fetch the list of available Deribit instruments."""
    return _get_default_client().get_available_instruments(
        currency=currency,
        kind=kind,
        expired=expired,
    )


def get_full_chain(
    currency: str = "BTC",
    min_open_interest: float = 0.0,
) -> pd.DataFrame:
    """Fetch a normalized Deribit options chain as a dataframe."""
    return _get_default_client().get_full_chain(
        currency=currency,
        min_open_interest=min_open_interest,
    )


def get_iv_surface_data(
    currency: str = "BTC",
    min_open_interest: float = 0.0,
) -> pd.DataFrame:
    """Fetch the option-chain slice needed to fit an IV surface."""
    return _get_default_client().get_iv_surface_data(
        currency=currency,
        min_open_interest=min_open_interest,
    )


def get_btc_price() -> float:
    """Fetch current BTC spot price in USD from CoinGecko."""
    return _get_default_client().get_btc_price()


def get_btc_volatility(days: int = 90, window: int = 30, trading_days: int = 365) -> float:
    """Fetch BTC spot history and return annualized realized volatility."""
    return _get_default_client().get_btc_volatility(
        days=days,
        window=window,
        trading_days=trading_days,
    )
