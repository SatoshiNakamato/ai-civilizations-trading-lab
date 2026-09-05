"""Contracts binding probabilistic forecasts to precise market events."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .arena import ForecastCommitment
from .market_events import MarketEvent


@dataclass(frozen=True)
class BoundForecast:
    commitment: ForecastCommitment
    event: MarketEvent
    contract_hash: str

    @property
    def forecast_id(self) -> str:
        return self.commitment.forecast_id


def bind_forecast(commitment: ForecastCommitment, event: MarketEvent) -> BoundForecast:
    if commitment.created_at != event.created_at:
        raise ValueError("forecast and market event must share the same creation timestamp")
    if commitment.market != event.symbol:
        raise ValueError("forecast market does not match event symbol")
    if commitment.horizon != event.horizon:
        raise ValueError("forecast horizon does not match event horizon")
    payload = f"{commitment.commitment}|{event.event_id}|{event.direction}|{event.threshold:.12g}"
    return BoundForecast(commitment, event, sha256(payload.encode()).hexdigest())


class ForecastContractRegistry:
    """Immutable registry of event definitions attached to forecast commitments."""

    def __init__(self) -> None:
        self._contracts: dict[str, BoundForecast] = {}

    def register(self, bound: BoundForecast) -> BoundForecast:
        existing = self._contracts.get(bound.forecast_id)
        if existing is not None:
            if existing.contract_hash != bound.contract_hash:
                raise ValueError("forecast is already bound to a different event")
            return existing
        self._contracts[bound.forecast_id] = bound
        return bound

    def get(self, forecast_id: str) -> BoundForecast:
        return self._contracts[forecast_id]

    def snapshot(self) -> dict:
        return {"contracts": len(self._contracts), "forecast_ids": list(self._contracts)}
