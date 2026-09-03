from __future__ import annotations

from dataclasses import dataclass
from time import time

from .intelligence import MarketIntelligence, VenueQuote


@dataclass
class ArbitrageFinding:
    symbol: str
    buy_venue: str
    sell_venue: str
    buy_price: float
    sell_price: float
    gross_spread_pct: float
    estimated_cost_pct: float
    net_spread_pct: float
    observed_at: float


class ArbitrageResearch:
    """Research-only arbitrage detector. It never places orders."""

    def __init__(self, min_net_spread_pct: float = 0.05, estimated_cost_pct: float = 0.10):
        self.min_net_spread_pct = min_net_spread_pct
        self.estimated_cost_pct = estimated_cost_pct
        self.market = MarketIntelligence()

    def ingest_quotes(self, quotes: list[VenueQuote]) -> list[ArbitrageFinding]:
        self.market.ingest(quotes)
        findings = []
        for opportunity in self.market.scan_arbitrage():
            net = opportunity.spread_pct - self.estimated_cost_pct
            if net >= self.min_net_spread_pct:
                findings.append(ArbitrageFinding(
                    opportunity.symbol,
                    opportunity.buy_venue,
                    opportunity.sell_venue,
                    opportunity.buy_price,
                    opportunity.sell_price,
                    opportunity.spread_pct,
                    self.estimated_cost_pct,
                    net,
                    time(),
                ))
        return findings
