import pytest

from markets.data import MarketDataAdapter, MarketObservation


def test_market_data_normalizes_external_rows():
    adapter = MarketDataAdapter("feed://exchange", lambda symbol: [
        {"symbol": symbol.lower(), "observed_at": 20, "price": 101, "observation_id": "b"},
        {"symbol": symbol, "observed_at": 10, "price": 100, "observation_id": "a"},
    ])
    observations = adapter.observations("BTCUSDT")
    assert [x.observation_id for x in observations] == ["a", "b"]
    assert observations[0].symbol == "BTCUSDT"
    assert observations[0].source == "feed://exchange"


def test_market_observation_rejects_invalid_values():
    with pytest.raises(ValueError):
        MarketObservation("BTCUSDT", 10, 0, "feed", "1")
    with pytest.raises(ValueError):
        MarketObservation("BTCUSDT", 10, 100, "", "1")


def test_adapter_rejects_malformed_external_rows():
    adapter = MarketDataAdapter("feed", lambda _: [{"symbol": "BTCUSDT", "price": 100}])
    with pytest.raises(ValueError, match="invalid market observation"):
        adapter.observations("BTCUSDT")
