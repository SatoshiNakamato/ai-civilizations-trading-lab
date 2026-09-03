from __future__ import annotations

from dataclasses import dataclass, asdict
from .real_data import PublicMarketData
from .features import compute_features
from .walk_forward import evaluate_directional


@dataclass
class AlphaCandidate:
    symbol: str
    interval: str
    hypothesis: str
    observations: int
    return_pct: float
    drawdown_pct: float
    score: float


class AlphaResearchLab:
    """Generates research candidates from observed data; never places orders."""
    def __init__(self, provider: PublicMarketData | None = None):
        self.provider = provider or PublicMarketData()
        self.history: list[AlphaCandidate] = []

    def scan(self, symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"), intervals=("15m", "1h", "4h"), limit=200):
        out = []
        for symbol in symbols:
            for interval in intervals:
                snap = self.provider.snapshot(symbol, interval, limit)
                candles = snap["candles"]
                features = compute_features(candles)
                closes = [float(c["close"]) for c in candles]
                result = evaluate_directional(closes)
                c = AlphaCandidate(symbol, interval, "directional-continuation", len(closes), result.total_return * 100, result.max_drawdown * 100, result.score)
                self.history.append(c)
                out.append(c)
        return sorted(out, key=lambda x: x.score, reverse=True)

    def snapshot(self):
        return {"candidates": len(self.history), "top": [asdict(x) for x in sorted(self.history, key=lambda x: x.score, reverse=True)[:20]]}
