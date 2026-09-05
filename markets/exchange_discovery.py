"""Exchange metadata discovery without coupling AEON to one venue."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping


@dataclass(frozen=True)
class ExchangePair:
    symbol: str
    base_asset: str
    quote_asset: str
    status: str
    exchange: str


class ExchangeDiscoveryAdapter:
    """Normalize an exchange's symbol metadata into venue-aware market pairs."""

    def __init__(self, exchange: str, fetch_metadata: Callable[[], Iterable[Mapping[str, Any]]]) -> None:
        if not exchange.strip():
            raise ValueError("exchange name is required")
        self.exchange = exchange.strip()
        self._fetch_metadata = fetch_metadata

    def discover(self) -> tuple[ExchangePair, ...]:
        pairs: list[ExchangePair] = []
        for row in self._fetch_metadata():
            try:
                symbol = str(row["symbol"]).strip().upper()
                base = str(row["baseAsset"]).strip().upper()
                quote = str(row["quoteAsset"]).strip().upper()
                status = str(row.get("status", "TRADING")).strip().upper()
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("invalid exchange symbol metadata") from exc
            if not symbol or not base or not quote:
                continue
            pairs.append(ExchangePair(symbol, base, quote, status, self.exchange))
        return tuple(sorted(pairs, key=lambda p: p.symbol))

    def trading_pairs(self) -> tuple[ExchangePair, ...]:
        """Return active pairs while preserving venue metadata."""
        return tuple(p for p in self.discover() if p.status == "TRADING")

    def symbols(self) -> tuple[str, ...]:
        return tuple(p.symbol for p in self.trading_pairs())
