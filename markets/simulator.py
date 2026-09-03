from __future__ import annotations

from dataclasses import dataclass
from random import Random


@dataclass
class MarketState:
    tick: int
    price: float
    volatility: float
    regime: str


class MarketWorld:
    """Small deterministic market world used for research and backtesting."""

    def __init__(self, seed: int = 7, initial_price: float = 100.0):
        self.rng = Random(seed)
        self.price = initial_price
        self.tick = 0
        self.history: list[float] = [initial_price]

    def step(self) -> MarketState:
        self.tick += 1
        regime = "trend" if self.tick // 20 % 2 == 0 else "mean_revert"
        drift = 0.0015 if regime == "trend" else -0.0005 * ((self.price - 100.0) / 10.0)
        shock = self.rng.gauss(0.0, 0.01)
        self.price *= max(0.5, 1.0 + drift + shock)
        self.history.append(self.price)
        window = self.history[-20:]
        returns = [(b / a) - 1.0 for a, b in zip(window, window[1:])]
        volatility = (sum(r * r for r in returns) / max(1, len(returns))) ** 0.5
        return MarketState(self.tick, self.price, volatility, regime)
