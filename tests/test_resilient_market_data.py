from markets.real_data import PublicMarketData


def test_snapshot_falls_back_when_public_api_is_unreachable(monkeypatch):
    provider = PublicMarketData(timeout=1)

    def fail(_url):
        raise OSError("network unreachable")

    monkeypatch.setattr(provider, "_get_json", fail)
    snapshot = provider.snapshot("BTCUSDT", "4h", 20)

    assert snapshot["mode"] == "offline"
    assert snapshot["source"] == "deterministic offline fallback"
    assert len(snapshot["candles"]) == 20
    assert snapshot["ticker"]["offline"] is True
    assert snapshot["live_error"] == "OSError"


def test_snapshot_can_disable_fallback(monkeypatch):
    provider = PublicMarketData(timeout=1)
    monkeypatch.setenv("AEON_MARKET_OFFLINE_FALLBACK", "false")
    monkeypatch.setattr(provider, "_get_json", lambda _url: (_ for _ in ()).throw(OSError("offline")))

    try:
        provider.snapshot("BTCUSDT", "4h", 5)
    except OSError as exc:
        assert str(exc) == "offline"
    else:
        raise AssertionError("offline fallback should be disabled")
