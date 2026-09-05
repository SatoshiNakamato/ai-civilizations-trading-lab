import pytest

from civilizations.arena import CivilizationArena
from civilizations.forecast_contract import ForecastContractRegistry, bind_forecast
from civilizations.market_events import MarketEvent


def test_forecast_can_only_bind_to_matching_event():
    arena = CivilizationArena()
    commitment = arena.commit("CIV-A", "A1", "BTCUSDT", "4h", .7, created_at=10)
    event = MarketEvent("BTCUSDT", "4h", "above", 100000, 10)
    bound = bind_forecast(commitment, event)
    assert bound.forecast_id == commitment.forecast_id
    assert len(bound.contract_hash) == 64


def test_mismatched_event_is_rejected():
    arena = CivilizationArena()
    commitment = arena.commit("CIV-A", "A1", "BTCUSDT", "4h", .7, created_at=10)
    with pytest.raises(ValueError, match="market"):
        bind_forecast(commitment, MarketEvent("ETHUSDT", "4h", "above", 1000, 10))
    with pytest.raises(ValueError, match="horizon"):
        bind_forecast(commitment, MarketEvent("BTCUSDT", "1h", "above", 100000, 10))


def test_registry_rejects_rebinding_to_different_contract():
    arena = CivilizationArena()
    commitment = arena.commit("CIV-A", "A1", "BTCUSDT", "4h", .7, created_at=10)
    registry = ForecastContractRegistry()
    registry.register(bind_forecast(commitment, MarketEvent("BTCUSDT", "4h", "above", 100000, 10)))
    different = bind_forecast(commitment, MarketEvent("BTCUSDT", "4h", "below", 100000, 10))
    with pytest.raises(ValueError, match="different event"):
        registry.register(different)
