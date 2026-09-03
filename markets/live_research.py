from __future__ import annotations

from dataclasses import dataclass, asdict
from time import time

from .features import compute_features
from .real_data import PublicMarketData
from .walk_forward import evaluate_directional


@dataclass
class MarketFinding:
    symbol: str
    interval: str
    trend: float
    volatility: float
    validation_score: float
    max_drawdown: float
    observations: int
    retrieved_at: float


class LiveResearchScout:
    """Research-only scanner using real public observations."""

    def __init__(self, provider: PublicMarketData | None = None):
        self.provider = provider or PublicMarketData()
        self.findings: list[MarketFinding] = []

    def scan(self, symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"), intervals=("15m", "1h", "4h"), limit=200):
        results = []
        for symbol in symbols:
            for interval in intervals:
                snapshot = self.provider.snapshot(symbol, interval, limit)
                candles = snapshot["candles"]
                closes = [float(c["close"]) for c in candles]
                features = compute_features(candles)
                validation = evaluate_directional(closes)
                finding = MarketFinding(symbol, interval, features["trend"], features["volatility"], validation.score, validation.max_drawdown, len(candles), snapshot["retrieved_at"])
                self.findings.append(finding)
                results.append(finding)
        return sorted(results, key=lambda x: x.validation_score, reverse=True)

    def snapshot(self):
        return {"findings": len(self.findings), "latest": [asdict(x) for x in self.findings[-20:]], "timestamp": time()}
