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
    """Read-only public quotes from multiple exchanges."""

    def __init__(self, timeout: int = 8):
        self.timeout = timeout

    def _get(self, url: str):
        req = urllib.request.Request(url, headers={"User-Agent": "ai-civilizations-trading-lab/1.0"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode())

    def binance(self, symbol: str) -> VenueQuote:
        q = urllib.parse.urlencode({"symbol": symbol.upper()})
        x = self._get("https://api.binance.com/api/v3/ticker/bookTicker?" + q)
        return VenueQuote("BINANCE", symbol.upper(), float(x["bidPrice"]), float(x["askPrice"]), time.time())

    def kraken(self, symbol: str) -> VenueQuote:
        # Map common USDT symbols to Kraken's public pair names.
        pair = {"BTCUSDT": "XBTUSDT", "ETHUSDT": "ETHUSDT", "SOLUSDT": "SOLUSDT"}.get(symbol.upper(), symbol.upper())
        data = self._get("https://api.kraken.com/0/public/Ticker?" + urllib.parse.urlencode({"pair": pair}))
        result = data.get("result", {})
        if not result:
            raise ValueError(f"Kraken returned no quote for {pair}")
        row = next(iter(result.values()))
        return VenueQuote("KRAKEN", symbol.upper(), float(row["b"][0]), float(row["a"][0]), time.time())


class CrossExchangeArbitrageLab:
    """Find research-only executable-looking cross-venue spreads.

    A result is marked executable only when both quotes are fresh and the
    estimated net spread is positive. It never submits orders or moves funds.
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
            quotes: list[VenueQuote] = []
            for getter in (self.provider.binance, self.provider.kraken):
                try:
                    quotes.append(getter(symbol))
                except Exception:
                    continue
            if len(quotes) < 2:
                continue
            for buy in quotes:
                for sell in quotes:
                    if buy.venue == sell.venue or buy.ask <= 0 or sell.bid <= 0:
                        continue
                    gross = (sell.bid / buy.ask - 1) * 100
                    cost = self.fee_pct * 2 + self.slippage_pct * 2
                    fresh = max(time.time() - buy.timestamp, time.time() - sell.timestamp) <= self.max_age_seconds
                    net = gross - cost
                    executable = fresh and net > 0
                    reason = "fresh positive net spread" if executable else ("stale quote" if not fresh else "net spread not positive after estimated costs")
                    out.append(CrossExchangeOpportunity(symbol, buy.venue, sell.venue, buy.ask, sell.bid, gross, cost, net, executable, reason))
        return sorted(out, key=lambda x: x.net_spread_pct, reverse=True)
