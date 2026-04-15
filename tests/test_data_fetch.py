from datetime import datetime, timezone

import pandas as pd

from crypto_bs.data_fetch import DeribitClient


def test_get_option_data_normalizes_ticker_payload(monkeypatch):
    client = DeribitClient(rate_limit_per_second=0)

    def fake_deribit_get(endpoint, params=None, cache_ttl=None):
        assert endpoint == "ticker"
        assert params == {"instrument_name": "BTC-01MAY26-100000-C"}
        return {
            "result": {
                "mark_price": 0.061,
                "mark_iv": 72.0,
                "best_bid_price": 0.059,
                "best_ask_price": 0.063,
                "underlying_price": 98000.0,
                "open_interest": 240.0,
            }
        }

    monkeypatch.setattr(client, "_deribit_get", fake_deribit_get)

    option = client.get_option_data("BTC-01MAY26-100000-C")

    assert option["mark_price"] == 0.061
    assert option["implied_volatility"] == 0.72
    assert option["bid_price"] == 0.059
    assert option["ask_price"] == 0.063
    assert option["underlying_price"] == 98000.0
    assert option["open_interest"] == 240.0


def test_get_full_chain_builds_filtered_dataframe(monkeypatch):
    client = DeribitClient(rate_limit_per_second=0)
    expiry = datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc)
    as_of = datetime(2026, 4, 10, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(
        client,
        "get_instruments",
        lambda **kwargs: [
            {
                "instrument_name": "BTC-01MAY26-100000-C",
                "base_currency": "BTC",
                "strike": 100000.0,
                "option_type": "call",
                "expiration_timestamp": expiry.timestamp() * 1000.0,
            },
            {
                "instrument_name": "BTC-01MAY26-100000-P",
                "base_currency": "BTC",
                "strike": 100000.0,
                "option_type": "put",
                "expiration_timestamp": expiry.timestamp() * 1000.0,
            },
        ],
    )

    def fake_deribit_get(endpoint, params=None, cache_ttl=None):
        assert endpoint == "get_book_summary_by_currency"
        return {
            "result": [
                {
                    "instrument_name": "BTC-01MAY26-100000-C",
                    "bid_price": 0.055,
                    "ask_price": 0.065,
                    "mark_price": 0.061,
                    "mark_iv": 70.0,
                    "underlying_price": 99000.0,
                    "open_interest": 200.0,
                    "volume": 12.0,
                },
                {
                    "instrument_name": "BTC-01MAY26-100000-P",
                    "bid_price": 0.051,
                    "ask_price": 0.063,
                    "mark_price": 0.057,
                    "mark_iv": 74.0,
                    "underlying_price": 99000.0,
                    "open_interest": 15.0,
                    "volume": 4.0,
                },
            ]
        }

    monkeypatch.setattr(client, "_deribit_get", fake_deribit_get)

    chain = client.get_full_chain(min_open_interest=100.0, as_of=as_of)

    assert list(chain["instrument_name"]) == ["BTC-01MAY26-100000-C"]
    assert chain.loc[0, "mid_price"] == 0.06
    assert chain.loc[0, "implied_volatility"] == 0.70
    assert 0.05 < chain.loc[0, "time_to_maturity"] < 0.07


def test_get_iv_surface_data_keeps_only_positive_iv_rows(monkeypatch):
    client = DeribitClient(rate_limit_per_second=0)
    chain = pd.DataFrame(
        [
            {
                "instrument_name": "BTC-01MAY26-100000-C",
                "expiry": datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc),
                "strike": 100000.0,
                "time_to_maturity": 21 / 365,
                "option_type": "call",
                "underlying_price": 99000.0,
                "mark_price": 0.061,
                "mid_price": 0.060,
                "implied_volatility": 0.70,
                "open_interest": 200.0,
            },
            {
                "instrument_name": "BTC-01MAY26-110000-C",
                "expiry": datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc),
                "strike": 110000.0,
                "time_to_maturity": 21 / 365,
                "option_type": "call",
                "underlying_price": 99000.0,
                "mark_price": 0.041,
                "mid_price": 0.041,
                "implied_volatility": 0.0,
                "open_interest": 150.0,
            },
            {
                "instrument_name": "BTC-01MAY26-90000-P",
                "expiry": datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc),
                "strike": 90000.0,
                "time_to_maturity": 21 / 365,
                "option_type": "put",
                "underlying_price": None,
                "mark_price": 0.018,
                "mid_price": 0.019,
                "implied_volatility": 0.82,
                "open_interest": 90.0,
            },
        ]
    )
    monkeypatch.setattr(client, "get_full_chain", lambda **kwargs: chain)

    surface = client.get_iv_surface_data()

    assert list(surface["instrument_name"]) == ["BTC-01MAY26-100000-C"]
    assert list(surface.columns) == [
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


def test_get_btc_volatility_from_history_returns_positive_value(monkeypatch):
    client = DeribitClient(rate_limit_per_second=0)
    prices = pd.Series(
        [
            100.0,
            102.0,
            101.0,
            104.0,
            103.0,
            106.0,
            108.0,
            107.0,
            110.0,
            112.0,
            115.0,
            113.0,
            116.0,
            118.0,
            117.0,
            120.0,
            123.0,
            125.0,
            124.0,
            128.0,
        ],
        index=pd.date_range("2026-03-01", periods=20, tz="UTC"),
    )
    monkeypatch.setattr(client, "get_historical_prices", lambda **kwargs: prices)

    hv = client.get_btc_volatility(days=20, window=10, trading_days=365)

    assert hv > 0


# --- v1.1.0 new tests ---

def test_cache_does_not_exceed_max_size(monkeypatch):
    """NEW-04: cache evicts entries before exceeding max_cache_size."""
    client = DeribitClient(rate_limit_per_second=0, max_cache_size=3)
    call_count = 0

    def fake_get(url, params=None, timeout=10):
        nonlocal call_count
        call_count += 1

        class FakeResp:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return {"result": call_count}

        return FakeResp()

    monkeypatch.setattr(client.session, "get", fake_get)

    # Fill cache beyond max_cache_size
    for i in range(10):
        client._request_json(
            base_url="https://test.example/",
            endpoint=f"ep_{i}",
            params={"q": i},
            cache_ttl=60.0,
        )

    assert len(client._cache) <= client.max_cache_size


def test_user_agent_is_not_hardcoded():
    """NEW-02: User-Agent header does not contain the old hardcoded version string."""
    client = DeribitClient(rate_limit_per_second=0)
    ua = client.session.headers.get("User-Agent", "")
    assert "crypto_bs/" in ua
    assert "0.9.0" not in ua
