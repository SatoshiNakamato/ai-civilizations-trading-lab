from __future__ import annotations

from dataclasses import dataclass
import os
import time
from typing import Any

import ccxt

from civilizations.email_alerts import AlertCandidate, EmailAlertGateway
from civilizations.opportunities import Opportunity, OpportunityEngine


DEFAULT_EXCHANGES = (
    "binance", "bybit", "okx", "kucoin", "gateio",
    "mexc", "bitget", "htx", "kraken", "coinbase",
)


@dataclass(frozen=True)
class MarketQuote:
    exchange: str
    symbol: str
    bid: float
    ask: float
    bid_volume: float
    ask_volume: float
    timestamp: float


class MultiExchangeArbitrageScanner:
    """Keyless public spot-market arbitrage scanner across many exchanges.

    Market data is public: no API credentials are used and this component never
    submits an order. It discovers cross-exchange price dislocations and emits
    actionable information alerts for manual execution.
    """

    def __init__(
        self,
        engine: OpportunityEngine | None = None,
        alert_gateway: EmailAlertGateway | None = None,
        exchanges: tuple[str, ...] | None = None,
        quote_currencies: tuple[str, ...] = ("USDT", "USDC", "USD"),
        min_volume_usd: float = 2_500.0,
        min_net_edge: float = 0.003,
        timeout_ms: int = 8_000,
        refresh_seconds: float = 20.0,
    ):
        self.engine = engine or OpportunityEngine()
        self.alert_gateway = alert_gateway
        names = exchanges or tuple(
            x.strip().lower() for x in os.getenv(
                "CIVILIZATION_ARBITRAGE_EXCHANGES", ",".join(DEFAULT_EXCHANGES)
            ).split(",") if x.strip()
        )
        self.exchange_names = names
        self.quote_currencies = tuple(x.upper() for x in quote_currencies)
        self.min_volume_usd = float(min_volume_usd)
        self.min_net_edge = float(min_net_edge)
        self.timeout_ms = int(timeout_ms)
        self.refresh_seconds = float(refresh_seconds)
        self._clients: dict[str, Any] = {}
        self._markets: dict[str, set[str]] = {}
        self._quotes: dict[str, list[MarketQuote]] = {}
        self._last_refresh = 0.0
        self.last_opportunities: list[Opportunity] = []
        self.scans = 0
        self.errors: dict[str, int] = {}
        self.alerts_sent = 0

    def _client(self, name: str):
        if name in self._clients:
            return self._clients[name]
        cls = getattr(ccxt, name)
        client = cls({"enableRateLimit": True, "timeout": self.timeout_ms})
        self._clients[name] = client
        return client

    def _load_markets(self, name: str) -> set[str]:
        if name in self._markets:
            return self._markets[name]
        try:
            markets = self._client(name).load_markets()
            symbols = {
                symbol for symbol, market in markets.items()
                if market.get("spot")
                and market.get("active", True)
                and any(symbol.endswith("/" + q) for q in self.quote_currencies)
            }
            self._markets[name] = symbols
            return symbols
        except Exception as exc:
            self.errors[name] = self.errors.get(name, 0) + 1
            return set()

    @staticmethod
    def _quote(name: str, symbol: str, ticker: dict) -> MarketQuote | None:
        try:
            bid = float(ticker.get("bid") or 0.0)
            ask = float(ticker.get("ask") or 0.0)
            if bid <= 0 or ask <= 0 or ask < bid:
                return None
            bid_volume = float(ticker.get("bidVolume") or 0.0)
            ask_volume = float(ticker.get("askVolume") or 0.0)
            ts = float(ticker.get("timestamp") or time.time() * 1000.0) / 1000.0
            return MarketQuote(name, symbol, bid, ask, bid_volume, ask_volume, ts)
        except (TypeError, ValueError):
            return None

    def _refresh(self) -> None:
        now = time.time()
        if now - self._last_refresh < self.refresh_seconds:
            return
        self._last_refresh = now
        for name in self.exchange_names:
            try:
                client = self._client(name)
                symbols = self._load_markets(name)
                if not symbols:
                    continue
                if client.has.get("fetchTickers"):
                    tickers = client.fetch_tickers(list(symbols))
                else:
                    tickers = {}
                    # Fallback for exchanges without bulk tickers. Keep the
                    # public-data scan bounded by the exchange's own markets.
                    for symbol in symbols:
                        try:
                            tickers[symbol] = client.fetch_ticker(symbol)
                        except Exception:
                            continue
                for symbol, ticker in tickers.items():
                    q = self._quote(name, symbol, ticker)
                    if q is None:
                        continue
                    # Require enough visible quote-side depth when available.
                    quote_volume = max(q.bid * q.bid_volume, q.ask * q.ask_volume)
                    if quote_volume and quote_volume < self.min_volume_usd:
                        continue
                    self._quotes.setdefault(symbol, [])
                    self._quotes[symbol] = [x for x in self._quotes[symbol] if x.exchange != name]
                    self._quotes[symbol].append(q)
            except Exception:
                self.errors[name] = self.errors.get(name, 0) + 1

        cutoff = now - 60.0
        for symbol in list(self._quotes):
            self._quotes[symbol] = [q for q in self._quotes[symbol] if q.timestamp >= cutoff]
            if not self._quotes[symbol]:
                del self._quotes[symbol]

    def _opportunities(self) -> list[Opportunity]:
        fee = float(os.getenv("CIVILIZATION_ARBITRAGE_FEE", "0.001"))
        candidates: list[Opportunity] = []
        for symbol, quotes in self._quotes.items():
            if len(quotes) < 2:
                continue
            buy = min(quotes, key=lambda q: q.ask)
            sell = max(quotes, key=lambda q: q.bid)
            if buy.exchange == sell.exchange:
                continue
            gross = (sell.bid - buy.ask) / buy.ask
            net = gross - 2.0 * fee
            if net < self.min_net_edge:
                continue
            asset = symbol.split("/")[0]
            candidates.append(Opportunity(
                opportunity_id="", category="arbitrage", asset=asset,
                summary=f"Live {symbol} cross-exchange spread: buy {buy.exchange}, sell {sell.exchange}",
                confidence=min(0.99, 0.85 + min(net, 0.10)), risk=0.25,
                gross_edge=gross, fees=2.0 * fee, slippage=0.0, liquidity=1.0,
                sources=[f"ccxt://{buy.exchange}/{symbol}", f"ccxt://{sell.exchange}/{symbol}"],
                agents=["MULTI-EXCHANGE-SCOUT"], buy_venue=buy.exchange,
                sell_venue=sell.exchange, buy_price=buy.ask, sell_price=sell.bid,
            ))
        return sorted(candidates, key=lambda x: x.net_edge, reverse=True)

    def _alert(self, opportunity: Opportunity) -> bool:
        if not self.alert_gateway or opportunity.net_edge < self.min_net_edge:
            return False
        result = self.engine.discover(opportunity)
        if result is None:
            return False
        result = self.engine.validate(result)
        if result.status != "validated":
            return False
        severity = self.engine.should_alert(result)
        if severity not in {"HIGH", "CRITICAL"}:
            return False
        candidate = AlertCandidate(
            title=f"Arbitrage: {result.asset} {result.buy_venue} → {result.sell_venue}",
            category="arbitrage",
            summary=(
                f"Live public-market opportunity detected. Buy {result.asset} on {result.buy_venue} "
                f"at ~{result.buy_price:.10g}; sell on {result.sell_venue} at ~{result.sell_price:.10g}. "
                f"Gross edge={result.gross_edge:.2%}; estimated fees={result.fees:.2%}; "
                f"estimated net edge={result.net_edge:.2%}. Verify order-book depth, transfer/settlement "
                "constraints and fees before manually acting."
            ),
            confidence=result.confidence, edge=result.net_edge, risk=result.risk,
            sources=tuple(result.sources), agent="MULTI-EXCHANGE-SCOUT",
            buy_venue=result.buy_venue, sell_venue=result.sell_venue,
            buy_price=result.buy_price, sell_price=result.sell_price,
        )
        sent = self.alert_gateway.send(candidate)
        if sent:
            self.alerts_sent += 1
        return sent

    def scan_once(self) -> Opportunity | None:
        self.scans += 1
        self._refresh()
        candidates = self._opportunities()
        self.last_opportunities = candidates[:25]
        for opportunity in candidates[:10]:
            self._alert(opportunity)
        return candidates[0] if candidates else None

    def snapshot(self) -> dict:
        return {
            "exchanges": list(self.exchange_names),
            "symbols": len(self._quotes),
            "scans": self.scans,
            "alerts_sent": self.alerts_sent,
            "errors": dict(self.errors),
            "last_opportunities": [o.__dict__.copy() for o in self.last_opportunities],
        }
