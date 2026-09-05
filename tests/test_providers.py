import pytest

from civilizations.arena import CivilizationArena
from civilizations.providers import CallableOutcomeProvider, ObservationPayload


def test_provider_normalizes_real_observation_payload():
    arena = CivilizationArena()
    commitment = arena.commit("CIV-A", "agent-1", "BTCUSDT", "4h", .7, created_at=10)
    provider = CallableOutcomeProvider("market-feed", lambda _: {"event": True, "observed_at": 20, "source": "feed://btc", "observation_id": "btc-20"})
    observation = provider.observe(commitment)
    assert observation.event is True
    assert observation.source == "feed://btc"
    assert observation.observation_id == "btc-20"


def test_provider_preserves_unavailable_state():
    arena = CivilizationArena()
    commitment = arena.commit("CIV-A", "agent-1", "BTCUSDT", "4h", .7, created_at=10)
    provider = CallableOutcomeProvider("market-feed", lambda _: None)
    assert provider.observe(commitment) is None


def test_provider_rejects_invalid_or_precommitment_observation():
    arena = CivilizationArena()
    commitment = arena.commit("CIV-A", "agent-1", "BTCUSDT", "4h", .7, created_at=10)
    invalid = CallableOutcomeProvider("market-feed", lambda _: ObservationPayload(True, 9, "feed://btc", "btc-9"))
    with pytest.raises(ValueError, match="predates"):
        invalid.observe(commitment)
