"""Market-pair discovery boundary used by AEON civilizations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class MarketPair:
    symbol: str
    status: str = "TRADING"


class MarketUniverse:
    """Discoverable market universe; symbols are not restricted to named assets."""

    def __init__(self, symbols: Iterable[str] | None = None, discover: Callable[[], Iterable[str]] | None = None) -> None:
        self._symbols = {s.strip().upper() for s in (symbols or ()) if s and s.strip()}
        self._discover = discover

    def refresh(self) -> tuple[str, ...]:
        if self._discover is not None:
            discovered = {s.strip().upper() for s in self._discover() if s and s.strip()}
            self._symbols = discovered
        return self.symbols

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(sorted(self._symbols))

    def __len__(self) -> int:
        return len(self._symbols)

    def require(self, symbol: str) -> str:
        normalized = symbol.strip().upper()
        if not normalized:
            raise ValueError("market symbol is required")
        if self._symbols and normalized not in self._symbols:
            raise ValueError(f"market pair is not in the discovered universe: {normalized}")
        return normalized

    def choose(self, index: int) -> str:
        if not self._symbols:
            raise RuntimeError("market universe is empty; configure pair discovery before forecasting")
        return self.symbols[index % len(self.symbols)]

    def snapshot(self) -> dict:
        return {"pairs": len(self), "symbols": list(self.symbols)}


def symbols_from_exchange_payload(payload: Iterable[dict]) -> tuple[str, ...]:
    """Normalize exchange pair metadata without imposing an asset allowlist."""
    return tuple(sorted({str(row["symbol"]).strip().upper() for row in payload if row.get("symbol") and row.get("status", "TRADING") == "TRADING"}))
