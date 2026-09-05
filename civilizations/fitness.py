"""Versioned fitness policies for robust civilization selection."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .scoring import ForecastScore


@dataclass(frozen=True)
class FitnessPolicy:
    version: str = "v1"
    brier_weight: float = 0.6
    log_loss_weight: float = 0.4
    minimum_forecasts: int = 5

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("policy version is required")
        if self.brier_weight < 0 or self.log_loss_weight < 0:
            raise ValueError("fitness weights cannot be negative")
        if self.brier_weight + self.log_loss_weight <= 0:
            raise ValueError("at least one fitness weight is required")
        if self.minimum_forecasts < 1:
            raise ValueError("minimum_forecasts must be positive")

    def evaluate(self, scores: list[ForecastScore]) -> float:
        if len(scores) < self.minimum_forecasts:
            return float("-inf")
        if any(not isfinite(x.brier) or not isfinite(x.log_loss) for x in scores):
            raise ValueError("non-finite forecast score")
        total = self.brier_weight + self.log_loss_weight
        mean_brier = sum(x.brier for x in scores) / len(scores)
        mean_log_loss = sum(x.log_loss for x in scores) / len(scores)
        # Higher fitness is better; both component losses are lower-is-better.
        return -(self.brier_weight * mean_brier + self.log_loss_weight * mean_log_loss) / total
