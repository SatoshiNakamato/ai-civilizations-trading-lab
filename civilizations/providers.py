"""Production-facing provider adapters for external Arena observations.

Providers are deliberately thin: they normalize independently observed data into
OutcomeObservation. They never score forecasts and never manufacture missing data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Any

from .arena import ForecastCommitment
from .outcomes import ExternalOutcomeProvider, OutcomeObservation


@dataclass(frozen=True)
class ObservationPayload:
    event: bool
    observed_at: float
    source: str
    observation_id: str


class CallableOutcomeProvider:
    """Adapter for a real external observation function.

    The callable is responsible for obtaining data from the external system. Returning
    None means the observation is not available yet; no fallback value is invented.
    """

    def __init__(self, name: str, observer: Callable[[ForecastCommitment], ObservationPayload | Mapping[str, Any] | None]) -> None:
        if not name.strip():
            raise ValueError("provider name is required")
        self.name = name
        self._observer = observer

    def observe(self, commitment: ForecastCommitment) -> OutcomeObservation | None:
        raw = self._observer(commitment)
        if raw is None:
            return None
        if isinstance(raw, ObservationPayload):
            payload = raw
        else:
            try:
                payload = ObservationPayload(
                    event=bool(raw["event"]),
                    observed_at=float(raw["observed_at"]),
                    source=str(raw["source"]),
                    observation_id=str(raw["observation_id"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("invalid external observation payload") from exc
        if not payload.source.strip() or not payload.observation_id.strip():
            raise ValueError("external observation requires source and observation_id")
        if payload.observed_at < commitment.created_at:
            raise ValueError("external observation predates forecast commitment")
        return OutcomeObservation(payload.event, payload.observed_at, payload.source, payload.observation_id)
