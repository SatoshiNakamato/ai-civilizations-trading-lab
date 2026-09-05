from __future__ import annotations

import json
import time
import urllib.error
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
    """Read-only public market data; no keys and no trading endpoints."""

    def __init__(self, timeout: int = 3):
        self.timeout = timeout

    def _get_json(self, url: str) -> Any:
        req = urllib.request.Request(url, headers={"User-Agent": "ai-civilizations-trading-lab/1.0"})
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _fallback_candles(limit: int, price: float = 100000.0) -> list[Candle]:
        now = time.time()
        return [Candle(now - (limit - i) * 3600, price, price, price, price, 0.0) for i in range(limit)]

    def _fallback_snapshot(self, symbol: str, interval: str, limit: int, error: Exception | None = None) -> dict[str, Any]:
        candles = self._fallback_candles(limit)
        message = type(error).__name__ + (f": {error}" if error else "")
        return {
            "source": "synthetic fallback (Binance unavailable)",
            "data_mode": "fallback",
            "symbol": symbol.upper(),
            "interval": interval,
            "retrieved_at": time.time(),
            "candles": [c.__dict__ for c in candles],
            "ticker": {"bidPrice": "100000.0", "askPrice": "100000.0", "bidQty": "0", "askQty": "0"},
            "error": message or None,
        }

    def binance_klines(self, symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 200) -> list[Candle]:
        safe_limit = min(max(limit, 1), 1000)
        query = urllib.parse.urlencode({"symbol": symbol.upper(), "interval": interval, "limit": safe_limit})
        try:
            data = self._get_json("https://api.binance.com/api/v3/klines?" + query)
            return [Candle(row[0] / 1000, float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])) for row in data]
        except (OSError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return self._fallback_candles(safe_limit)

    def binance_ticker(self, symbol: str = "BTCUSDT") -> dict[str, Any]:
        query = urllib.parse.urlencode({"symbol": symbol.upper()})
        return self._get_json("https://api.binance.com/api/v3/ticker/bookTicker?" + query)

    def snapshot(self, symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 200) -> dict[str, Any]:
        safe_limit = min(max(limit, 1), 1000)
        try:
            candles = self.binance_klines(symbol, interval, safe_limit)
            ticker = self.binance_ticker(symbol)
            return {
                "source": "Binance public API",
                "data_mode": "live",
                "symbol": symbol.upper(),
                "interval": interval,
                "retrieved_at": time.time(),
                "candles": [c.__dict__ for c in candles],
                "ticker": ticker,
                "error": None,
            }
        except (OSError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            return self._fallback_snapshot(symbol, interval, safe_limit, exc)
