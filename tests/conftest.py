"""Hermetic test fixtures: tests must never depend on external market APIs."""


class DeterministicMarketProvider:
    def snapshot(self, symbol="BTCUSDT", interval="4h", limit=500):
        candles = []
        for i in range(limit):
            price = 100.0 + i
            candles.append({"timestamp": float(i), "open": price, "high": price + 1, "low": price - 1, "close": price, "volume": 1000.0})
        return {"source": "deterministic-test-fixture", "symbol": symbol, "retrieved_at": 0.0, "candles": candles, "ticker": {}}
