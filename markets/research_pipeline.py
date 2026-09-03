from __future__ import annotations

from .features import compute_features
from .real_data import PublicMarketData
from .walk_forward import evaluate_directional


class RealMarketResearch:
    """Turns public observed market data into research evidence."""

    def __init__(self, provider: PublicMarketData | None = None):
        self.provider = provider or PublicMarketData()

    def investigate(self, symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 200) -> dict:
        snapshot = self.provider.snapshot(symbol, interval, limit)
        candles = snapshot["candles"]
        closes = [float(c["close"]) for c in candles]
        features = compute_features(candles)
        validation = evaluate_directional(closes)
        return {
            "symbol": symbol,
            "interval": interval,
            "source": snapshot["source"],
            "retrieved_at": snapshot["retrieved_at"],
            "features": features,
            "validation": validation.__dict__,
            "observations": len(candles),
        }
