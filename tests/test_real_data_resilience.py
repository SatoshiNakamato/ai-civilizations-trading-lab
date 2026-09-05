from markets.real_data import PublicMarketData


def test_klines_falls_back_on_network_failure(monkeypatch):
    provider = PublicMarketData(timeout=1)

    def fail(_url):
        raise TimeoutError("network timeout")

    monkeypatch.setattr(provider, "_get_json", fail)
    candles = provider.binance_klines("BTCUSDT", "1h", 5)
    assert len(candles) == 5
    assert all(c.close == 100000.0 for c in candles)


def test_snapshot_survives_network_failure(monkeypatch):
    provider = PublicMarketData(timeout=1)

    def fail(_url):
        raise OSError("network unavailable")

    monkeypatch.setattr(provider, "_get_json", fail)
    snapshot = provider.snapshot("BTCUSDT", "4h", 10)
    assert snapshot["data_mode"] == "fallback"
    assert len(snapshot["candles"]) == 10
    assert snapshot["ticker"]["bidPrice"] == "100000.0"
