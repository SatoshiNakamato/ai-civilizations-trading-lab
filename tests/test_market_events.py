import pytest

from civilizations.market_events import MarketEvent


def test_market_event_has_deterministic_identity():
    a = MarketEvent("BTCUSDT", "4h", "above", 100000, 10)
    b = MarketEvent("BTCUSDT", "4h", "above", 100000, 10)
    assert a.event_id == b.event_id


def test_above_event_is_evaluated_against_explicit_horizon():
    event = MarketEvent("BTCUSDT", "4h", "above", 100000, 10)
    assert event.evaluate(100001, 20) is True
    assert event.evaluate(99999, 20) is False


def test_below_event_is_evaluated_against_threshold():
    event = MarketEvent("BTCUSDT", "4h", "below", 100000, 10)
    assert event.evaluate(99999, 20) is True
    assert event.evaluate(100001, 20) is False


def test_event_rejects_pre_event_observation():
    event = MarketEvent("BTCUSDT", "4h", "above", 100000, 10)
    with pytest.raises(ValueError, match="predates"):
        event.evaluate(100001, 9)


def test_event_rejects_ambiguous_direction_and_threshold():
    with pytest.raises(ValueError):
        MarketEvent("BTCUSDT", "4h", "up", 100000, 10)
    with pytest.raises(ValueError):
        MarketEvent("BTCUSDT", "4h", "above", 0, 10)
