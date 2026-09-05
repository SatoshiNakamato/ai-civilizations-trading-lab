"""Strict probabilistic scoring for civilization forecasts."""
from __future__ import annotations

from dataclasses import dataclass
from math import log
from typing import Iterable


@dataclass(frozen=True)
class ForecastScore:
    probability: float
    outcome: bool
    brier: float
    log_loss: float


def score_forecast(probability: float, outcome: bool, *, floor: float = 1e-6) -> ForecastScore:
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between 0 and 1")
    if not 0.0 < floor < 0.5:
        raise ValueError("floor must be between 0 and 0.5")
    brier = (probability - float(outcome)) ** 2
    p = min(1.0 - floor, max(floor, probability))
    log_loss = -log(p if outcome else 1.0 - p)
    return ForecastScore(probability, outcome, brier, log_loss)


def aggregate_scores(rows: Iterable[ForecastScore]) -> dict[str, float | int]:
    values = list(rows)
    if not values:
        return {"count": 0, "brier": 0.0, "log_loss": 0.0}
    return {
        "count": len(values),
        "brier": sum(x.brier for x in values) / len(values),
        "log_loss": sum(x.log_loss for x in values) / len(values),
    }
