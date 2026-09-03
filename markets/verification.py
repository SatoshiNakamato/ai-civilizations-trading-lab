from __future__ import annotations

from dataclasses import dataclass
from .real_data import PublicMarketData
from .walk_forward import evaluate_directional


@dataclass
class VerificationResult:
    symbol: str
    interval: str
    samples: int
    score: float
    total_return: float
    max_drawdown: float
    passed: bool


class AlphaVerifier:
    def __init__(self, provider: PublicMarketData | None = None):
        self.provider = provider or PublicMarketData()

    def verify(self, symbol: str, interval: str, limit: int = 500) -> VerificationResult:
        snap = self.provider.snapshot(symbol, interval, limit)
        closes = [float(c["close"]) for c in snap["candles"]]
        result = evaluate_directional(closes)
        passed = result.trades >= 30 and result.score > 0 and result.total_return > 0
        return VerificationResult(symbol, interval, result.samples, result.score, result.total_return, result.max_drawdown, passed)
