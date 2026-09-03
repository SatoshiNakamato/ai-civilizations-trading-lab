from __future__ import annotations

from dataclasses import dataclass, asdict
from statistics import mean
from typing import Iterable


@dataclass(frozen=True)
class VenueQuote:
    venue: str
    symbol: str
    bid: float
    ask: float
    timestamp: float


@dataclass(frozen=True)
class ArbitrageOpportunity:
    symbol: str
    buy_venue: str
    sell_venue: str
    buy_price: float
    sell_price: float
    gross_spread: float
    spread_pct: float


class MarketIntelligence:
    """Research-only market intelligence for simulation/backtesting.

    It identifies price inconsistencies between supplied quotes. It does not
    place orders, sign transactions, access wallets, or move treasury funds.
    """

    def __init__(self):
        self.quotes: list[VenueQuote] = []
        self.opportunities: list[ArbitrageOpportunity] = []

    def ingest(self, quotes: Iterable[VenueQuote]) -> None:
        self.quotes.extend(quotes)

    def scan_arbitrage(self, min_spread_pct: float = 0.25) -> list[ArbitrageOpportunity]:
        grouped: dict[str, list[VenueQuote]] = {}
        for quote in self.quotes:
            if quote.bid > 0 and quote.ask > 0:
                grouped.setdefault(quote.symbol.upper(), []).append(quote)

        found: list[ArbitrageOpportunity] = []
        for symbol, quotes in grouped.items():
            for buy in quotes:
                for sell in quotes:
                    if buy.venue == sell.venue or sell.bid <= buy.ask:
                        continue
                    spread = sell.bid - buy.ask
                    pct = spread / buy.ask * 100
                    if pct >= min_spread_pct:
                        found.append(ArbitrageOpportunity(symbol, buy.venue, sell.venue, buy.ask, sell.bid, spread, pct))
        self.opportunities = sorted(found, key=lambda x: x.spread_pct, reverse=True)
        return self.opportunities

    def snapshot(self) -> dict:
        return {
            "quotes": len(self.quotes),
            "opportunities": len(self.opportunities),
            "top": [asdict(x) for x in self.opportunities[:10]],
            "average_spread_pct": round(mean(x.spread_pct for x in self.opportunities), 4) if self.opportunities else 0.0,
        }
