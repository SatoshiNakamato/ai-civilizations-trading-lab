import pytest

from markets.exchange_discovery import ExchangeDiscoveryAdapter


PAYLOAD = [
    {"symbol": "btcusdt", "baseAsset": "btc", "quoteAsset": "usdt", "status": "TRADING"},
    {"symbol": "ETHUSDC", "baseAsset": "ETH", "quoteAsset": "USDC", "status": "TRADING"},
    {"symbol": "OLDUSDT", "baseAsset": "OLD", "quoteAsset": "USDT", "status": "BREAK"},
]


def test_discovery_normalizes_and_preserves_all_trading_pairs():
    adapter = ExchangeDiscoveryAdapter("venue-x", lambda: PAYLOAD)
    assert adapter.symbols() == ("BTCUSDT", "ETHUSDC")
    pairs = adapter.trading_pairs()
    assert pairs[0].exchange == "venue-x"
    assert pairs[0].status == "TRADING"


def test_discovery_rejects_malformed_metadata():
    adapter = ExchangeDiscoveryAdapter("venue-x", lambda: [{"symbol": "BTCUSDT"}])
    with pytest.raises(ValueError, match="invalid exchange symbol metadata"):
        adapter.discover()


def test_discovery_does_not_apply_asset_allowlist():
    payload = [{"symbol": "NEARUSDC", "baseAsset": "NEAR", "quoteAsset": "USDC", "status": "TRADING"}]
    adapter = ExchangeDiscoveryAdapter("venue-x", lambda: payload)
    assert adapter.symbols() == ("NEARUSDC",)
