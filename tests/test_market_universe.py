import pytest

from markets.universe import MarketUniverse, symbols_from_exchange_payload


def test_universe_accepts_arbitrary_trading_pairs():
    universe = MarketUniverse(["BTCUSDT", "DOGEUSDT", "XRPUSDC", "ADAUSDT"])
    assert universe.symbols == ("ADAUSDT", "BTCUSDT", "DOGEUSDT", "XRPUSDC")
    assert universe.require("xrpusdc") == "XRPUSDC"


def test_universe_refreshes_from_external_discovery():
    pairs = ["BTCUSDT", "PEPEUSDT", "SOLBTC", "NEARUSDC"]
    universe = MarketUniverse(discover=lambda: pairs)
    assert universe.refresh() == tuple(sorted(pairs))
    assert universe.snapshot()["pairs"] == 4


def test_exchange_payload_filters_non_trading_pairs_only():
    payload = [
        {"symbol": "BTCUSDT", "status": "TRADING"},
        {"symbol": "DOGEUSDT", "status": "TRADING"},
        {"symbol": "OLDUSDT", "status": "BREAK"},
    ]
    assert symbols_from_exchange_payload(payload) == ("BTCUSDT", "DOGEUSDT")


def test_empty_universe_cannot_choose():
    with pytest.raises(RuntimeError, match="empty"):
        MarketUniverse().choose(0)
