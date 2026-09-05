"""Guards against duplicate, overlapping, and low-information forecasts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ForecastKey:
    civilization_id: str
    market: str
    horizon: str


def validate_forecast_batch(keys: Iterable[ForecastKey], *, max_per_market: int = 1) -> tuple[ForecastKey, ...]:
    """Validate forecast density independently for each civilization."""
    if max_per_market < 1:
        raise ValueError("max_per_market must be positive")
    seen: set[ForecastKey] = set()
    counts: dict[tuple[str, str, str], int] = {}
    result: list[ForecastKey] = []
    for key in keys:
        if not all((key.civilization_id, key.market, key.horizon)):
            raise ValueError("forecast identity fields are required")
        if key in seen:
            raise ValueError("duplicate forecast identity")
        bucket = (key.civilization_id, key.market, key.horizon)
        if counts.get(bucket, 0) >= max_per_market:
            raise ValueError("forecast density limit exceeded")
        seen.add(key)
        counts[bucket] = counts.get(bucket, 0) + 1
        result.append(key)
    return tuple(result)
