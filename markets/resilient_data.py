from __future__ import annotations

import hashlib
import math
import random
import time
from typing import Any

from .real_data import Candle


def synthetic_snapshot(symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 200) -> dict[str, Any]:
    """Create deterministic, clearly-labelled candles when public market data is unreachable."""
    symbol = symbol.upper()
    limit = min(max(int(limit), 1), 1000)
    seed = int.from_bytes(hashlib.sha256(f"{symbol}:{interval}".encode()).digest()[:8], "big")
    rng = random.Random(seed)
    price = {"BTCUSDT": 60000.0, "ETHUSDT": 3000.0, "SOLUSDT": 140.0}.get(symbol, 100.0)
    candles: list[Candle] = []
    now = time.time()
    step_seconds = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}.get(interval, 3600)
    start = now - (limit * step_seconds)
    for i in range(limit):
        drift = rng.uniform(-0.012, 0.012)
        open_price = price
        close = max(0.01, open_price * (1.0 + drift))
        high = max(open_price, close) * (1.0 + rng.uniform(0.0, 0.004))
        low = min(open_price, close) * (1.0 - rng.uniform(0.0, 0.004))
        volume = rng.uniform(100.0, 1000.0)
        candles.append(Candle(start + i * step_seconds, open_price, high, low, close, volume))
        price = close
    return {
        "source": "deterministic offline fallback",
        "mode": "offline",
        "symbol": symbol,
        "interval": interval,
        "retrieved_at": now,
        "candles": [c.__dict__ for c in candles],
        "ticker": {"symbol": symbol, "bidPrice": str(price), "askPrice": str(price), "offline": True},
    }
