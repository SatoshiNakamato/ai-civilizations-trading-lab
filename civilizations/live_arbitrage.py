from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Iterable

from .email_alerts import AlertCandidate, EmailAlertGateway
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


@dataclass(frozen=True)
class OrderBook:
    venue: str
    asset: str
    bids: tuple[tuple[float, float], ...]
    asks: tuple[tuple[float, float], ...]
    timestamp: float = field(default_factory=time.time)

    @property
    def best_bid(self) -> float:
        return self.bids[0][0] if self.bids else 0.0

    @property
    def best_ask(self) -> float:
        return self.asks[0][0] if self.asks else 0.0


@dataclass(frozen=True)
class FeeSchedule:
    """Conservative taker fee assumptions, expressed as decimal fractions."""
    coinbase: float = 0.006
    kraken: float = 0.004

    def for_venue(self, venue: str) -> float:
        return float(getattr(self, venue.lower(), 0.006))


class PublicQuoteFeed:
    """Dependency-free live quote/order-book feed using public exchange endpoints."""

    def __init__(self, timeout: float = 8.0, opener: Callable | None = None):
        self.timeout = timeout
        self._open = opener or urllib.request.urlopen

    def _get_json(self, url: str) -> dict:
        request = urllib.request.Request(url, headers={"User-Agent": "civilization-arbitrage/0.2"})
        with self._open(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def coinbase(self, product: str = "BTC-USD") -> Quote:
        data = self._get_json(f"https://api.exchange.coinbase.com/products/{product}/ticker")
        return Quote("coinbase", product, float(data["bid"]), float(data["ask"]))

    def kraken(self, pair: str = "XBTUSD") -> Quote:
        data = self._get_json(f"https://api.kraken.com/0/public/Ticker?pair={pair}")
        result = next(iter(data["result"].values()))
        return Quote("kraken", "BTC-USD", float(result["b"][0]), float(result["a"][0]))

    def coinbase_book(self, product: str = "BTC-USD", level: int = 2) -> OrderBook:
        data = self._get_json(f"https://api.exchange.coinbase.com/products/{product}/book?level={level}")
        return OrderBook(
            "coinbase", product,
            tuple((float(p), float(s)) for p, s, *_ in data.get("bids", [])),
            tuple((float(p), float(s)) for p, s, *_ in data.get("asks", [])),
        )

    def kraken_book(self, pair: str = "XBTUSD", count: int = 25) -> OrderBook:
        data = self._get_json(f"https://api.kraken.com/0/public/Depth?pair={pair}&count={count}")
        result = next(iter(data["result"].values()))
        return OrderBook(
            "kraken", "BTC-USD",
            tuple((float(p), float(s)) for p, s, *_ in result.get("bids", [])),
            tuple((float(p), float(s)) for p, s, *_ in result.get("asks", [])),
        )

    def snapshot(self) -> list[Quote]:
        quotes: list[Quote] = []
        for loader in (self.coinbase, self.kraken):
            try:
                quotes.append(loader())
            except Exception:
                continue
        return quotes

    def order_books(self) -> list[OrderBook]:
        books: list[OrderBook] = []
        for loader in (self.coinbase_book, self.kraken_book):
            try:
                books.append(loader())
            except Exception:
                continue
        return books


def _weighted_buy(asks: Iterable[tuple[float, float]], quantity: float) -> float | None:
    remaining = quantity
    cost = 0.0
    for price, size in asks:
        if price <= 0 or size <= 0:
            continue
        take = min(remaining, size)
        cost += take * price
        remaining -= take
        if remaining <= 1e-12:
            return cost / quantity
    return None


def _weighted_sell(bids: Iterable[tuple[float, float]], quantity: float) -> float | None:
    remaining = quantity
    proceeds = 0.0
    for price, size in bids:
        if price <= 0 or size <= 0:
            continue
        take = min(remaining, size)
        proceeds += take * price
        remaining -= take
        if remaining <= 1e-12:
            return proceeds / quantity
    return None


class LiveArbitrageScanner:
    """Find research-only cross-venue opportunities from live quotes/order books."""

    def __init__(
        self,
        feed: PublicQuoteFeed | None = None,
        engine: OpportunityEngine | None = None,
        fees: FeeSchedule | None = None,
        alert_gateway: EmailAlertGateway | None = None,
    ):
        self.feed = feed or PublicQuoteFeed()
        self.engine = engine or OpportunityEngine()
        self.fees = fees or FeeSchedule()
        self.alert_gateway = alert_gateway

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
            opportunity_id="", category="arbitrage", asset="BTC",
            summary=f"Live BTC spread: buy {cheapest.venue}, sell {best.venue}",
            confidence=0.90, risk=0.25, gross_edge=gross, fees=fees,
            slippage=slippage, liquidity=1.0,
            sources=[f"live://{q.venue}" for q in quotes], agents=["LIVE-MARKET-FEED"],
            buy_venue=cheapest.venue, sell_venue=best.venue,
            buy_price=cheapest.ask, sell_price=best.bid,
        )

    @staticmethod
    def from_order_books(
        books: list[OrderBook],
        quantity: float = 0.01,
        fee_schedule: FeeSchedule | None = None,
    ) -> Opportunity | None:
        if quantity <= 0 or len(books) < 2:
            return None
        fees = fee_schedule or FeeSchedule()
        candidates: list[Opportunity] = []
        for buy in books:
            buy_avg = _weighted_buy(buy.asks, quantity)
            if buy_avg is None or buy_avg <= 0:
                continue
            for sell in books:
                if buy.venue == sell.venue:
                    continue
                sell_avg = _weighted_sell(sell.bids, quantity)
                if sell_avg is None or sell_avg <= 0:
                    continue
                buy_fee = fees.for_venue(buy.venue)
                sell_fee = fees.for_venue(sell.venue)
                gross = (sell_avg - buy_avg) / buy_avg
                fee_drag = buy_fee + sell_fee
                net = gross - fee_drag
                liquidity = min(1.0, quantity / max(quantity, sum(s for _, s in buy.asks) or quantity))
                candidates.append(Opportunity(
                    opportunity_id="", category="arbitrage", asset="BTC",
                    summary=f"Executable BTC book spread: buy {buy.venue}, sell {sell.venue}, size={quantity:g} BTC",
                    confidence=0.95, risk=0.20, gross_edge=gross, fees=fee_drag,
                    slippage=max(0.0, gross - ((sell.best_bid - buy.best_ask) / buy.best_ask if buy.best_ask else gross)),
                    liquidity=liquidity,
                    sources=[f"live-book://{buy.venue}", f"live-book://{sell.venue}"],
                    agents=["LIVE-ORDERBOOK-FEED"], buy_venue=buy.venue,
                    sell_venue=sell.venue, buy_price=buy_avg, sell_price=sell_avg,
                ))
        if not candidates:
            return None
        return max(candidates, key=lambda o: o.net_edge)

    def scan_once(self) -> Opportunity | None:
        # Prefer depth-aware data, but retain compatibility with lightweight
        # quote-feed implementations used by tests and simulations.
        if hasattr(self.feed, "order_books"):
            books = self.feed.order_books()
            candidate = self.from_order_books(books, fee_schedule=self.fees)
        else:
            candidate = self.from_quotes(self.feed.snapshot())
            if candidate is not None:
                candidate.fees = self.fees.for_venue(candidate.buy_venue) + self.fees.for_venue(candidate.sell_venue)

        if candidate is None:
            return None
        candidate = self.engine.discover(candidate)
        if candidate is None:
            return None
        candidate = self.engine.validate(candidate)
        if self.alert_gateway and candidate.status == "validated":
            severity = self.engine.should_alert(candidate)
            if severity in {"HIGH", "CRITICAL"}:
                self.alert_gateway.send(AlertCandidate(
                    title=candidate.summary, category="arbitrage", summary=(
                        f"Validated live opportunity. Buy {candidate.buy_venue} at ~{candidate.buy_price:.2f}; "
                        f"sell {candidate.sell_venue} at ~{candidate.sell_price:.2f}. "
                        f"Estimated net edge: {candidate.net_edge:.2%}. Research-only; do not execute automatically."
                    ), confidence=candidate.confidence, edge=candidate.net_edge,
                    risk=candidate.risk, sources=tuple(candidate.sources), agent="LIVE-ORDERBOOK-FEED",
                ))
        return candidate

    def snapshot(self) -> dict:
        return self.engine.snapshot()
