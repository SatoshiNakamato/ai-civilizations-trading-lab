from dataclasses import dataclass

import pytest

from civilizations.arena import CivilizationArena
from civilizations.outcomes import OutcomeObservation, OutcomeResolver


@dataclass
class Provider:
    name: str = "independent-source"
    observation: OutcomeObservation | None = None

    def observe(self, commitment):
        return self.observation


def test_resolver_requires_external_provenance():
    arena = CivilizationArena()
    commitment = arena.commit("CIV-001", "A001", "BTCUSDT", "4h", .7, created_at=10)
    arena.submit(commitment)
    provider = Provider(observation=OutcomeObservation(True, 20, "", "obs-1"))
    with pytest.raises(ValueError, match="provenance"):
        OutcomeResolver(provider).resolve(arena, commitment.forecast_id)


def test_resolver_records_external_observation():
    arena = CivilizationArena()
    commitment = arena.commit("CIV-001", "A001", "BTCUSDT", "4h", .7, created_at=10)
    arena.submit(commitment)
    provider = Provider(observation=OutcomeObservation(True, 20, "external://market-feed", "obs-1"))
    outcome = OutcomeResolver(provider).resolve(arena, commitment.forecast_id)
    assert outcome is not None
    assert outcome.event is True
    assert outcome.source == "external://market-feed"


def test_unavailable_external_observation_does_not_resolve():
    arena = CivilizationArena()
    commitment = arena.commit("CIV-001", "A001", "BTCUSDT", "4h", .7, created_at=10)
    arena.submit(commitment)
    assert OutcomeResolver(Provider()).resolve(arena, commitment.forecast_id) is None
    assert not arena.outcomes
