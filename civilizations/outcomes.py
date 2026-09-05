"""External outcome interfaces for the AEON Civilization Arena."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .arena import ForecastCommitment, ForecastOutcome


@dataclass(frozen=True)
class OutcomeObservation:
    event: bool
    observed_at: float
    source: str
    observation_id: str


class ExternalOutcomeProvider(Protocol):
    name: str

    def observe(self, commitment: ForecastCommitment) -> OutcomeObservation | None:
        """Return an independently observed outcome, or None if unavailable."""
        ...


class OutcomeResolver:
    """Resolve forecasts only through an explicitly supplied external provider."""

    def __init__(self, provider: ExternalOutcomeProvider) -> None:
        self.provider = provider

    def resolve(self, arena, forecast_id: str) -> ForecastOutcome | None:
        commitment = arena.commitments.get(forecast_id)
        if commitment is None:
            raise KeyError(f"unknown forecast: {forecast_id}")
        observation = self.provider.observe(commitment)
        if observation is None:
            return None
        if not observation.source.strip():
            raise ValueError("external observation must contain provenance")
        if not observation.observation_id.strip():
            raise ValueError("external observation must contain an observation_id")
        return arena.resolve(ForecastOutcome(
            forecast_id=forecast_id,
            event=bool(observation.event),
            observed_at=float(observation.observed_at),
            source=observation.source,
        ))
