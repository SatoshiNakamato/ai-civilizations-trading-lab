from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskDecision:
    allowed: bool
    size_fraction: float
    reason: str


class RiskEngine:
    def __init__(self, max_position_fraction: float = 0.10, max_drawdown: float = 0.20):
        self.max_position_fraction = max_position_fraction
        self.max_drawdown = max_drawdown

    def assess(self, volatility: float, drawdown: float, confidence: float) -> RiskDecision:
        if drawdown >= self.max_drawdown:
            return RiskDecision(False, 0.0, "drawdown protection")
        if volatility >= 0.08:
            return RiskDecision(False, 0.0, "volatility gate")
        size = min(self.max_position_fraction, max(0.0, confidence) * self.max_position_fraction)
        return RiskDecision(size > 0.0, size, "within configured risk limits")
