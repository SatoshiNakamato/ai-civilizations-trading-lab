import pytest

from civilizations.anti_gaming import ForecastKey, validate_forecast_batch


def test_duplicate_identity_is_rejected():
    key = ForecastKey("CIV-A", "BTCUSDT", "4h")
    with pytest.raises(ValueError, match="duplicate"):
        validate_forecast_batch([key, key])


def test_density_limit_is_per_civilization_market_across_horizons():
    rows = [
        ForecastKey("CIV-A", "BTCUSDT", "4h"),
        ForecastKey("CIV-A", "BTCUSDT", "1h"),
    ]
    with pytest.raises(ValueError, match="density"):
        validate_forecast_batch(rows, max_per_market=1)


def test_different_civilizations_can_forecast_same_market():
    rows = [ForecastKey("CIV-A", "BTCUSDT", "4h"), ForecastKey("CIV-B", "BTCUSDT", "4h")]
    assert validate_forecast_batch(rows) == tuple(rows)


def test_distinct_markets_are_allowed():
    rows = [ForecastKey("CIV-A", "BTCUSDT", "4h"), ForecastKey("CIV-A", "ETHUSDT", "4h")]
    assert validate_forecast_batch(rows) == tuple(rows)
