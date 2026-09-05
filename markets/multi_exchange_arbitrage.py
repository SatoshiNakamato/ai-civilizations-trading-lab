from __future__ import annotations

from dataclasses import dataclass
import importlib
import os
import time
from typing import Any

from civilizations.email_alerts import AlertCandidate, EmailAlertGateway
from civilizations.opportunities import Opportunity, OpportunityEngine

DEFAULT_EXCHANGES = (
    "binance", "bybit", "okx", "kucoin", "gateio",
    "mexc", "bitget", "htx", "kraken", "coinbase",
)

try:
    ccxt = importlib.import_module("ccxt")
    CCXT_IMPORT_ERROR: Exception | None = None
except Exception as exc:
    ccxt = None
    CCXT_IMPORT_ERROR = exc


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
    """Public spot-market arbitrage scanner across configured exchanges.

    The scanner discovers the active spot market universe, refreshes public
    bid/ask data, compares cross-exchange spreads, and sends alerts after the
    existing opportunity/risk gates pass. It never submits orders.
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
        ticker_batch_size: int = 100,
    ):
        self.engine = engine or OpportunityEngine()
        self.alert_gateway = alert_gateway
        names = exchanges or tuple(
            x.strip().lower() for x in os.getenv(
                "CIVILIZATION_ARBITRAGE_EXCHANGES", ",".join(DEFAULT_EXCHANGES)
            ).split(",") if x.strip()
        )
        self.exchange_names = tuple(dict.fromkeys(names))
        configured_quotes = quote_currencies or tuple(
            x.strip().upper() for x in os.getenv(
                "CIVILIZATION_ARBITRAGE_QUOTES", "USDT,USDC,USD"
            ).split(",") if x.strip()
        )
        self.quote_currencies = tuple(dict.fromkeys(configured_quotes))
        self.min_volume_usd = float(min_volume_usd)
        self.min_net_edge = float(min_net_edge)
        self.timeout_ms = int(timeout_ms)
        self.refresh_seconds = float(refresh_seconds)
        self.ticker_batch_size = max(1, int(ticker_batch_size))
        self._clients: dict[str, Any] = {}
        self._markets: dict[str, set[str]] = {}
        self._quotes: dict[str, list[MarketQuote]] = {}
        self._last_refresh = 0.0
        self.last_opportunities: list[Opportunity] = []
        self.scans = 0
        self.errors: dict[str, int] = {}
        self.alerts_sent = 0

    def _error(self, name: str) -> None:
        self.errors[name] = self.errors.get(name, 0) + 1

    def _client(self, name: str):
        if name in self._clients:
            return self._clients[name]
        if ccxt is None:
            raise RuntimeError(f"ccxt unavailable: {CCXT_IMPORT_ERROR!r}")
        try:
            cls = getattr(ccxt, name)
        except AttributeError as exc:
            raise RuntimeError(f"Unsupported CCXT exchange: {name}") from exc
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
        except Exception:
            self._error(name)
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

    def _fetch_tickers(self, client: Any, symbols: set[str]) -> dict[str, dict]:
        """Fetch as much of the public ticker universe as the exchange allows."""
        if not symbols:
            return {}
        if not client.has.get("fetchTickers"):
            output: dict[str, dict] = {}
            for symbol in symbols:
                try:
                    output[symbol] = client.fetch_ticker(symbol)
                except Exception:
                    continue
            return output

        # Most exchanges expose all public tickers through fetch_tickers().
        # This avoids issuing one HTTP request per token on large markets.
        try:
            all_tickers = client.fetch_tickers()
            if isinstance(all_tickers, dict) and all_tickers:
                return {symbol: ticker for symbol, ticker in all_tickers.items() if symbol in symbols}
        except Exception:
            pass

        # Some exchanges require an explicit symbol list. Bound each request
        # and fall back to individual tickers only for failed batches.
        output: dict[str, dict] = {}
        ordered = sorted(symbols)
        for start in range(0, len(ordered), self.ticker_batch_size):
            batch = ordered[start:start + self.ticker_batch_size]
            try:
                tickers = client.fetch_tickers(batch)
                if isinstance(tickers, dict):
                    output.update(tickers)
                    continue
            except Exception:
                pass
            for symbol in batch:
                try:
                    output[symbol] = client.fetch_ticker(symbol)
                except Exception:
                    continue
        return output

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
                tickers = self._fetch_tickers(client, symbols)
                for symbol, ticker in tickers.items():
                    q = self._quote(name, symbol, ticker)
                    if q is None:
                        continue
                    quote_volume = max(q.bid * q.bid_volume, q.ask * q.ask_volume)
                    if quote_volume and quote_volume < self.min_volume_usd:
                        continue
                    current = [x for x in self._quotes.get(symbol, []) if x.exchange != name]
                    current.append(q)
                    self._quotes[symbol] = current
            except Exception:
                self._error(name)

        cutoff = now - max(60.0, self.refresh_seconds * 3.0)
        for symbol in list(self._quotes):
            fresh = [q for q in self._quotes[symbol] if q.timestamp >= cutoff]
            if fresh:
                self._quotes[symbol] = fresh
            else:
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
                "constraints and fees before acting."
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
            "quote_currencies": list(self.quote_currencies),
            "market_universe": {name: len(symbols) for name, symbols in self._markets.items()},
            "symbols": len(self._quotes),
            "scans": self.scans,
            "alerts_sent": self.alerts_sent,
            "errors": dict(self.errors),
            "ccxt_available": ccxt is not None,
            "last_opportunities": [o.__dict__.copy() for o in self.last_opportunities],
        }
