"""Precise, immutable event definitions for real market outcome evaluation."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class MarketEvent:
    """A forecastable binary market event with an explicit evaluation horizon."""

    symbol: str
    horizon: str
    direction: str
    threshold: float
    created_at: float

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if not self.horizon.strip():
            raise ValueError("horizon is required")
        if self.direction not in {"above", "below"}:
            raise ValueError("direction must be above or below")
        if self.threshold <= 0:
            raise ValueError("threshold must be positive")

    @property
    def event_id(self) -> str:
        payload = f"{self.symbol}|{self.horizon}|{self.direction}|{self.threshold:.12g}|{self.created_at:.6f}"
        return sha256(payload.encode()).hexdigest()[:24]

    def evaluate(self, observed_value: float, observed_at: float) -> bool:
        if observed_at < self.created_at:
            raise ValueError("observation predates market event")
        return observed_value > self.threshold if self.direction == "above" else observed_value < self.threshold
