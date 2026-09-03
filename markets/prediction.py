from __future__ import annotations

from dataclasses import dataclass
from math import log


@dataclass(frozen=True)
class PredictionMarket:
    market_id: str
    question: str
    probability: float
    volume: float = 0.0


@dataclass(frozen=True)
class PredictionAssessment:
    market_id: str
    model_probability: float
    market_probability: float
    edge: float
    information_score: float


def assess_market(market: PredictionMarket, model_probability: float) -> PredictionAssessment:
    p = max(0.001, min(0.999, model_probability))
    m = max(0.001, min(0.999, market.probability))
    edge = p - m
    # Symmetric information distance; useful for ranking research candidates.
    information = abs(log(p / m))
    return PredictionAssessment(market.market_id, p, m, edge, information)
