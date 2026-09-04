from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

from .opportunities import Opportunity, OpportunityEngine


@dataclass(frozen=True)
class Quote:
    venue: str
    asset: str
    bid: float
    ask: float
    timestamp: float = field(default_factory=time.time)

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2


class PublicQuoteFeed:
    """Small dependency-free live quote feed using public exchange endpoints."""

    def __init__(self, timeout: float = 8.0, opener: Callable | None = None):
        self.timeout = timeout
        self._open = opener or urllib.request.urlopen

    def _get_json(self, url: str) -> dict:
        request = urllib.request.Request(url, headers={"User-Agent": "civilization-arbitrage/0.1"})
        with self._open(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def coinbase(self, product: str = "BTC-USD") -> Quote:
        data = self._get_json(f"https://api.exchange.coinbase.com/products/{product}/ticker")
        return Quote("coinbase", product, float(data["bid"]), float(data["ask"]))

    def kraken(self, pair: str = "XBTUSD") -> Quote:
        data = self._get_json(f"https://api.kraken.com/0/public/Ticker?pair={pair}")
        result = next(iter(data["result"].values()))
        return Quote("kraken", "BTC-USD", float(result["b"][0]), float(result["a"][0]))

    def snapshot(self) -> list[Quote]:
        quotes: list[Quote] = []
        for loader in (self.coinbase, self.kraken):
            try:
                quotes.append(loader())
            except Exception:
                # A single venue outage must not take down the scanner.
                continue
        return quotes


class LiveArbitrageScanner:
    """Turn simultaneous public quotes into research-only arbitrage candidates."""

    def __init__(self, feed: PublicQuoteFeed | None = None, engine: OpportunityEngine | None = None):
        self.feed = feed or PublicQuoteFeed()
        self.engine = engine or OpportunityEngine()

    @staticmethod
    def from_quotes(quotes: list[Quote], fees: float = 0.0, slippage: float = 0.0) -> Opportunity | None:
        if len(quotes) < 2:
            return None
        best = max(quotes, key=lambda q: q.bid)
        cheapest = min(quotes, key=lambda q: q.ask)
        if best.venue == cheapest.venue or cheapest.ask <= 0:
            return None
        gross = (best.bid - cheapest.ask) / cheapest.ask
        return Opportunity(
            opportunity_id="",
            category="arbitrage",
            asset="BTC",
            summary=f"Live BTC spread: buy {cheapest.venue}, sell {best.venue}",
            confidence=0.90,
            risk=0.25,
            gross_edge=gross,
            fees=fees,
            slippage=slippage,
            liquidity=1.0,
            sources=[f"live://{q.venue}" for q in quotes],
            agents=["LIVE-MARKET-FEED"],
            buy_venue=cheapest.venue,
            sell_venue=best.venue,
            buy_price=cheapest.ask,
            sell_price=best.bid,
        )

    def scan_once(self) -> Opportunity | None:
        quotes = self.feed.snapshot()
        candidate = self.from_quotes(quotes)
        if candidate is None:
            return None
        candidate = self.engine.discover(candidate)
        if candidate is None:
            return None
        return self.engine.validate(candidate)

    def snapshot(self) -> dict:
        return self.engine.snapshot()
