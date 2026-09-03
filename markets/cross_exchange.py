from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class VenueQuote:
    venue: str
    symbol: str
    bid: float
    ask: float
    timestamp: float


@dataclass(frozen=True)
class CrossExchangeOpportunity:
    symbol: str
    buy_venue: str
    sell_venue: str
    buy_ask: float
    sell_bid: float
    gross_spread_pct: float
    estimated_cost_pct: float
    net_spread_pct: float
    executable: bool
    reason: str


class PublicCrossExchangeData:
    """Read-only public top-of-book quotes from several venues."""

    def __init__(self, timeout: int = 8):
        self.timeout = timeout
        self.last_errors: dict[str, str] = {}

    def _get(self, url: str):
        req = urllib.request.Request(url, headers={"User-Agent": "ai-civilizations-trading-lab/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode())

    def binance(self, symbol: str) -> VenueQuote:
        x = self._get("https://api.binance.com/api/v3/ticker/bookTicker?" + urllib.parse.urlencode({"symbol": symbol.upper()}))
        return VenueQuote("BINANCE", symbol.upper(), float(x["bidPrice"]), float(x["askPrice"]), time.time())

    def kraken(self, symbol: str) -> VenueQuote:
        pair = {"BTCUSDT": "XBTUSDT", "ETHUSDT": "ETHUSDT", "SOLUSDT": "SOLUSDT"}.get(symbol.upper(), symbol.upper())
        data = self._get("https://api.kraken.com/0/public/Ticker?" + urllib.parse.urlencode({"pair": pair}))
        if data.get("error"):
            raise ValueError("Kraken: " + ", ".join(data["error"]))
        result = data.get("result", {})
        if not result:
            raise ValueError(f"Kraken returned no quote for {pair}")
        row = next(iter(result.values()))
        return VenueQuote("KRAKEN", symbol.upper(), float(row["b"][0]), float(row["a"][0]), time.time())

    def coinbase(self, symbol: str) -> VenueQuote:
        pair = symbol.upper().replace("USDT", "-USD")
        x = self._get("https://api.exchange.coinbase.com/products/" + urllib.parse.quote(pair) + "/ticker")
        return VenueQuote("COINBASE", symbol.upper(), float(x["bid"]), float(x["ask"]), time.time())

    def collect(self, symbol: str) -> list[VenueQuote]:
        self.last_errors = {}
        quotes: list[VenueQuote] = []
        for name, getter in (("BINANCE", self.binance), ("KRAKEN", self.kraken), ("COINBASE", self.coinbase)):
            try:
                q = getter(symbol)
                if q.bid > 0 and q.ask >= q.bid:
                    quotes.append(q)
                else:
                    self.last_errors[name] = "invalid bid/ask"
            except Exception as exc:
                self.last_errors[name] = str(exc)
        return quotes


class CrossExchangeArbitrageLab:
    """Research-only cross-exchange arbitrage detector.

    It compares buy-side asks against another venue's sell-side bids. It
    accounts for configurable round-trip fees and slippage estimates and
    never places orders or moves funds.
    """

    def __init__(self, provider: PublicCrossExchangeData | None = None, fee_pct: float = 0.20, slippage_pct: float = 0.10, max_age_seconds: float = 10.0):
        self.provider = provider or PublicCrossExchangeData()
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct
        self.max_age_seconds = max_age_seconds

    def inspect(self, symbols: list[str] | None = None) -> list[CrossExchangeOpportunity]:
        symbols = symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        out: list[CrossExchangeOpportunity] = []
        for symbol in symbols:
            quotes = self.provider.collect(symbol)
            for buy in quotes:
                for sell in quotes:
                    if buy.venue == sell.venue or buy.ask <= 0 or sell.bid <= 0:
                        continue
                    gross = (sell.bid / buy.ask - 1.0) * 100.0
                    cost = self.fee_pct * 2.0 + self.slippage_pct * 2.0
                    age = max(time.time() - buy.timestamp, time.time() - sell.timestamp)
                    fresh = age <= self.max_age_seconds
                    net = gross - cost
                    executable = fresh and net > 0.0
                    if executable:
                        reason = "fresh positive net spread after estimated costs"
                    elif not fresh:
                        reason = "quote freshness check failed"
                    else:
                        reason = "spread does not cover estimated fees and slippage"
                    out.append(CrossExchangeOpportunity(symbol, buy.venue, sell.venue, buy.ask, sell.bid, gross, cost, net, executable, reason))
        return sorted(out, key=lambda x: x.net_spread_pct, reverse=True)

    def diagnostics(self, symbols: list[str] | None = None) -> dict:
        symbols = symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        venues: dict[str, int] = {}
        errors: dict[str, dict[str, str]] = {}
        for symbol in symbols:
            quotes = self.provider.collect(symbol)
            for q in quotes:
                venues[q.venue] = venues.get(q.venue, 0) + 1
            if self.provider.last_errors:
                errors[symbol] = dict(self.provider.last_errors)
        return {"symbols": symbols, "venue_quotes": venues, "errors": errors}
