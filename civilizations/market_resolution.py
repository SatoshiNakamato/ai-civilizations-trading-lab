"""Resolve precise forecast contracts from timestamped market observations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from markets.data import MarketObservation

from .forecast_contract import BoundForecast


@dataclass(frozen=True)
class ResolvedMarketEvent:
    forecast_id: str
    event_id: str
    observation_id: str
    observed_at: float
    observed_price: float
    source: str
    result: bool


class MarketEventResolver:
    """Select the first valid observation at or after an event's creation time."""

    def resolve(self, bound: BoundForecast, observations: Iterable[MarketObservation]) -> ResolvedMarketEvent | None:
        candidates = [x for x in observations if x.symbol == bound.event.symbol and x.observed_at >= bound.event.created_at]
        if not candidates:
            return None
        observation = min(candidates, key=lambda x: (x.observed_at, x.observation_id))
        result = bound.event.evaluate(observation.price, observation.observed_at)
        return ResolvedMarketEvent(
            forecast_id=bound.forecast_id,
            event_id=bound.event.event_id,
            observation_id=observation.observation_id,
            observed_at=observation.observed_at,
            observed_price=observation.price,
            source=observation.source,
            result=result,
        )
