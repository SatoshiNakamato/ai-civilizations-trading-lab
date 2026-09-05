"""Provider-neutral market observation and candle ingestion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping


@dataclass(frozen=True)
class MarketObservation:
    symbol: str
    observed_at: float
    price: float
    source: str
    observation_id: str

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.observed_at < 0:
            raise ValueError("observed_at must be non-negative")
        if self.price <= 0:
            raise ValueError("price must be positive")
        if not self.source.strip() or not self.observation_id.strip():
            raise ValueError("source and observation_id are required")


class MarketDataAdapter:
    """Normalize externally fetched market observations without scoring them."""

    def __init__(self, source: str, fetch: Callable[[str], Iterable[Mapping[str, Any]]]) -> None:
        if not source.strip():
            raise ValueError("source is required")
        self.source = source.strip()
        self._fetch = fetch

    def observations(self, symbol: str) -> tuple[MarketObservation, ...]:
        if not symbol.strip():
            raise ValueError("symbol is required")
        result: list[MarketObservation] = []
        for row in self._fetch(symbol.upper()):
            try:
                result.append(MarketObservation(
                    symbol=str(row["symbol"]).strip().upper(),
                    observed_at=float(row["observed_at"]),
                    price=float(row["price"]),
                    source=self.source,
                    observation_id=str(row["observation_id"]).strip(),
                ))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("invalid market observation payload") from exc
        return tuple(sorted(result, key=lambda x: (x.observed_at, x.observation_id)))
