from __future__ import annotations

from dataclasses import dataclass
import os
import time
from typing import Any

from civilizations.email_alerts import AlertCandidate, EmailAlertGateway
from civilizations.opportunities import Opportunity, OpportunityEngine


DEFAULT_EXCHANGES = (
    "binance", "bybit", "okx", "kucoin", "gateio", "mexc", "bitget",
    "htx", "kraken", "coinbase", "bitmart", "bingx", "phemex", "crypto_com",
)
DEFAULT_QUOTES = ("USDT", "USDC", "USD", "FDUSD", "USDE")


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
    """Public spot-market scanner across all active configured exchange markets.

    The scanner discovers every active spot symbol matching the configured quote
    currencies; it is not restricted to a hard-coded coin list. It never submits
    orders. CCXT is imported lazily so research/test modules can load without the
    live-market dependency installed.
    """

    def __init__(
        self,
        engine: OpportunityEngine | None = None,
        alert_gateway: EmailAlertGateway | None = None,
        exchanges: tuple[str, ...] | None = None,
        quote_currencies: tuple[str, ...] | None = None,
        min_volume_usd: float = 2_500.0,
        min_net_edge: float = 0.003,
        timeout_ms: int = 8_000,
        refresh_seconds: float = 20.0,
    ):
        self.engine = engine or OpportunityEngine()
        self.alert_gateway = alert_gateway
        configured = os.getenv("CIVILIZATION_ARBITRAGE_EXCHANGES", ",".join(DEFAULT_EXCHANGES))
        self.exchange_names = exchanges or tuple(x.strip().lower() for x in configured.split(",") if x.strip())
        configured_quotes = os.getenv("CIVILIZATION_ARBITRAGE_QUOTES", ",".join(DEFAULT_QUOTES))
        self.quote_currencies = quote_currencies or tuple(x.strip().upper() for x in configured_quotes.split(",") if x.strip())
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

    @staticmethod
    def _ccxt():
        try:
            import ccxt
        except ImportError as exc:
            raise RuntimeError(
                "CCXT is required for live multi-exchange scanning. Install it with "
                "`python -m pip install -r requirements.txt`."
            ) from exc
        return ccxt

    def _client(self, name: str):
        if name in self._clients:
            return self._clients[name]
        ccxt = self._ccxt()
        if not hasattr(ccxt, name):
            raise ValueError(f"Unsupported CCXT exchange: {name}")
        client = getattr(ccxt, name)({"enableRateLimit": True, "timeout": self.timeout_ms})
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
        except Exception:
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

    def _fetch_tickers(self, name: str, symbols: set[str]) -> dict[str, dict]:
        client = self._client(name)
        if not symbols:
            return {}
        if client.has.get("fetchTickers"):
            try:
                return client.fetch_tickers(list(symbols))
            except Exception:
                # Some exchanges cap symbols per request. Batch the full discovered
                # market universe instead of falling back to a tiny coin allow-list.
                result: dict[str, dict] = {}
                ordered = sorted(symbols)
                for start in range(0, len(ordered), 100):
                    try:
                        result.update(client.fetch_tickers(ordered[start:start + 100]))
                    except Exception:
                        continue
                return result
        result = {}
        for symbol in symbols:
            try:
                result[symbol] = client.fetch_ticker(symbol)
            except Exception:
                continue
        return result

    def _refresh(self) -> None:
        now = time.time()
        if now - self._last_refresh < self.refresh_seconds:
            return
        self._last_refresh = now
        for name in self.exchange_names:
            try:
                symbols = self._load_markets(name)
                for symbol, ticker in self._fetch_tickers(name, symbols).items():
                    quote = self._quote(name, symbol, ticker)
                    if quote is None:
                        continue
                    quote_volume = max(quote.bid * quote.bid_volume, quote.ask * quote.ask_volume)
                    if quote_volume and quote_volume < self.min_volume_usd:
                        continue
                    current = [q for q in self._quotes.get(symbol, []) if q.exchange != name]
                    current.append(quote)
                    self._quotes[symbol] = current
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
            category="arbitrage", summary=(
                f"Live public-market opportunity detected. Buy {result.asset} on {result.buy_venue} "
                f"at ~{result.buy_price:.10g}; sell on {result.sell_venue} at ~{result.sell_price:.10g}. "
                f"Gross edge={result.gross_edge:.2%}; estimated fees={result.fees:.2%}; "
                f"estimated net edge={result.net_edge:.2%}. Verify order-book depth, settlement "
                "constraints and fees before acting."
            ), confidence=result.confidence, edge=result.net_edge, risk=result.risk,
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
            "quotes": len(self._quotes),
            "market_sets": {name: len(symbols) for name, symbols in self._markets.items()},
            "scans": self.scans,
            "alerts_sent": self.alerts_sent,
            "errors": dict(self.errors),
            "last_opportunities": [o.__dict__.copy() for o in self.last_opportunities],
        }
