from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Candle:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float


class PublicMarketData:
    """Read-only public market data. Uses a labelled deterministic fallback offline."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def _get_json(self, url: str) -> Any:
        req = urllib.request.Request(url, headers={"User-Agent": "ai-civilizations-trading-lab/1.0"})
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def binance_klines(self, symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 200) -> list[Candle]:
        query = urllib.parse.urlencode({"symbol": symbol.upper(), "interval": interval, "limit": min(max(limit, 1), 1000)})
        data = self._get_json("https://api.binance.com/api/v3/klines?" + query)
        return [Candle(row[0] / 1000, float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])) for row in data]

    def binance_ticker(self, symbol: str = "BTCUSDT") -> dict[str, Any]:
        query = urllib.parse.urlencode({"symbol": symbol.upper()})
        return self._get_json("https://api.binance.com/api/v3/ticker/bookTicker?" + query)

    def snapshot(self, symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 200) -> dict[str, Any]:
        """Prefer live public data; keep the autonomous worker alive when the network is unavailable."""
        try:
            candles = self.binance_klines(symbol, interval, limit)
            ticker = self.binance_ticker(symbol)
            return {
                "source": "Binance public API",
                "mode": "live",
                "symbol": symbol.upper(),
                "retrieved_at": time.time(),
                "candles": [c.__dict__ for c in candles],
                "ticker": ticker,
            }
        except Exception as exc:
            if os.getenv("AEON_MARKET_OFFLINE_FALLBACK", "true").lower() not in {"1", "true", "yes", "on"}:
                raise
            from .resilient_data import synthetic_snapshot
            fallback = synthetic_snapshot(symbol, interval, limit)
            fallback["live_error"] = type(exc).__name__
            return fallback
