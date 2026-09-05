from civilizations.arena import CivilizationArena
from civilizations.forecast_contract import bind_forecast
from civilizations.market_events import MarketEvent
from civilizations.market_resolution import MarketEventResolver
from markets.data import MarketObservation


def test_resolution_binds_exact_observation_to_forecast():
    arena = CivilizationArena()
    commitment = arena.commit("CIV-A", "agent-1", "BTCUSDT", "4h", .8, created_at=10)
    event = MarketEvent("BTCUSDT", "4h", "above", 100000, 10)
    bound = bind_forecast(commitment, event)
    result = MarketEventResolver().resolve(bound, [
        MarketObservation("BTCUSDT", 12, 99999, "feed", "late"),
        MarketObservation("BTCUSDT", 11, 100001, "feed", "first"),
    ])
    assert result.forecast_id == commitment.forecast_id
    assert result.event_id == event.event_id
    assert result.observation_id == "first"
    assert result.result is True


def test_resolution_returns_none_without_matching_observation():
    arena = CivilizationArena()
    commitment = arena.commit("CIV-A", "agent-1", "ETHUSDC", "1h", .6, created_at=10)
    event = MarketEvent("ETHUSDC", "1h", "above", 3000, 10)
    bound = bind_forecast(commitment, event)
    assert MarketEventResolver().resolve(bound, [MarketObservation("BTCUSDT", 20, 100000, "feed", "btc")]) is None
