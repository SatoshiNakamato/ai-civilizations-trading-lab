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


@dataclass(frozen=True)
class DepthCheck:
    quantity: float
    buy_vwap: float
    sell_vwap: float
    buy_depth: float
    sell_depth: float
    observed_at: float
    buy_timestamp: float
    sell_timestamp: float


def _vwap(levels: list | tuple, quantity: float) -> tuple[float, float] | None:
    remaining = quantity
    notional = 0.0
    filled = 0.0
    for level in levels or ():
        if len(level) < 2:
            continue
        try:
            price, amount = float(level[0]), float(level[1])
        except (TypeError, ValueError):
            continue
        if price <= 0 or amount <= 0:
            continue
        take = min(remaining, amount)
        notional += take * price
        filled += take
        remaining -= take
        if remaining <= 1e-12:
            return notional / quantity, filled
    return None


class MultiExchangeArbitrageScanner:
    """Public spot-market arbitrage scanner with live depth verification.

    A candidate is not alertable merely because ticker bid/ask values cross.
    Before an alert is emitted, both venues must expose enough fresh public
    order-book depth for the configured notional and the post-fee executable
    edge must remain above the threshold. No order is ever submitted.
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
        self.orderbook_limit = max(5, int(os.getenv("CIVILIZATION_ARBITRAGE_ORDERBOOK_LIMIT", "25")))
        self.notional_usd = max(1.0, float(os.getenv("CIVILIZATION_ARBITRAGE_NOTIONAL_USD", "100")))
        self.max_quote_age_seconds = max(1.0, float(os.getenv("CIVILIZATION_ARBITRAGE_MAX_QUOTE_AGE_SECONDS", "10")))
        self._clients: dict[str, Any] = {}
        self._markets: dict[str, set[str]] = {}
        self._quotes: dict[str, list[MarketQuote]] = {}
        self._last_refresh = 0.0
        self.last_opportunities: list[Opportunity] = []
        self.scans = 0
        self.errors: dict[str, int] = {}
        self.alerts_sent = 0
        self.verified_count = 0
        self.rejected_depth = 0
        self.last_alerts_sent = 0

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
        try:
            all_tickers = client.fetch_tickers()
            if isinstance(all_tickers, dict) and all_tickers:
                return {symbol: ticker for symbol, ticker in all_tickers.items() if symbol in symbols}
        except Exception:
            pass
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

    def _depth_verify(self, buy: MarketQuote, sell: MarketQuote) -> DepthCheck | None:
        if buy.exchange == sell.exchange or buy.ask <= 0 or sell.bid <= 0:
            return None
        client_buy = self._client(buy.exchange)
        client_sell = self._client(sell.exchange)
        try:
            buy_book = client_buy.fetch_order_book(buy.symbol, self.orderbook_limit)
            sell_book = client_sell.fetch_order_book(sell.symbol, self.orderbook_limit)
        except Exception:
            self._error(f"depth:{buy.exchange}:{sell.exchange}")
            return None
        observed = time.time()
        def book_time(book: dict) -> float:
            raw = book.get("timestamp")
            try:
                return float(raw) / 1000.0 if raw is not None else observed
            except (TypeError, ValueError):
                return observed
        buy_ts = book_time(buy_book)
        sell_ts = book_time(sell_book)
        if observed - buy_ts > self.max_quote_age_seconds or observed - sell_ts > self.max_quote_age_seconds:
            self.rejected_depth += 1
            return None
        if buy_ts > observed + 2 or sell_ts > observed + 2:
            self.rejected_depth += 1
            return None
        if not buy_book.get("asks") or not sell_book.get("bids"):
            self.rejected_depth += 1
            return None
        try:
            target_qty = self.notional_usd / buy.ask
        except ZeroDivisionError:
            return None
        buy_vwap_result = _vwap(buy_book["asks"], target_qty)
        sell_vwap_result = _vwap(sell_book["bids"], target_qty)
        if buy_vwap_result is None or sell_vwap_result is None:
            self.rejected_depth += 1
            return None
        buy_vwap, buy_depth = buy_vwap_result
        sell_vwap, sell_depth = sell_vwap_result
        if buy_depth + 1e-12 < target_qty or sell_depth + 1e-12 < target_qty:
            self.rejected_depth += 1
            return None
        return DepthCheck(
            quantity=target_qty,
            buy_vwap=buy_vwap,
            sell_vwap=sell_vwap,
            buy_depth=buy_depth,
            sell_depth=sell_depth,
            observed_at=observed,
            buy_timestamp=buy_ts,
            sell_timestamp=sell_ts,
        )

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
            ticker_net = gross - 2.0 * fee
            if ticker_net < self.min_net_edge:
                continue
            depth = self._depth_verify(buy, sell)
            if depth is None:
                continue
            executable_gross = (depth.sell_vwap - depth.buy_vwap) / depth.buy_vwap
            slippage = max(0.0, gross - executable_gross)
            net = executable_gross - 2.0 * fee
            if net < self.min_net_edge:
                self.rejected_depth += 1
                continue
            asset = symbol.split("/")[0]
            candidate = Opportunity(
                opportunity_id="", category="arbitrage", asset=asset,
                summary=f"Verified live {symbol} cross-exchange opportunity: buy {buy.exchange}, sell {sell.exchange}",
                confidence=min(0.995, 0.90 + min(net, 0.095)), risk=0.20,
                gross_edge=gross, fees=2.0 * fee, slippage=slippage,
                liquidity=min(1.0, depth.quantity * buy.ask / max(self.notional_usd, 1.0)),
                sources=[
                    f"ccxt://{buy.exchange}/{buy.symbol}/orderbook",
                    f"ccxt://{sell.exchange}/{sell.symbol}/orderbook",
                ],
                agents=["MULTI-EXCHANGE-SCOUT", "DEPTH-VERIFIER"],
                buy_venue=buy.exchange, sell_venue=sell.exchange,
                buy_price=depth.buy_vwap, sell_price=depth.sell_vwap,
                observed_at=depth.observed_at, quantity=depth.quantity,
                notional_usd=depth.quantity * depth.buy_vwap,
                buy_depth=depth.buy_depth, sell_depth=depth.sell_depth,
                executable=True,
                verification=(
                    "Fresh public L2 order books verified on both venues; "
                    f"target quantity {depth.quantity:.12g}; VWAP route remains above "
                    f"{net:.3%} net edge after estimated taker fees. "
                    "Manual execution requires pre-funded balances on both venues."
                ),
            )
            candidates.append(candidate)
            self.verified_count += 1
        return sorted(candidates, key=lambda x: x.net_edge, reverse=True)

    def _alert(self, opportunity: Opportunity) -> bool:
        if not self.alert_gateway or not opportunity.executable or opportunity.net_edge < self.min_net_edge:
            return False
        result = self.engine.discover(opportunity)
        if result is None:
            return False
        result = self.engine.validate(result, min_net_edge=self.min_net_edge)
        if result.status != "validated" or not result.executable:
            return False
        severity = self.engine.should_alert(result)
        if severity not in {"HIGH", "CRITICAL"}:
            return False
        observed = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(result.observed_at))
        candidate = AlertCandidate(
            title=f"Verified arbitrage: {result.asset} {result.buy_venue} → {result.sell_venue}",
            category="arbitrage",
            summary=(
                f"EXECUTABLE public-market opportunity observed {observed}. Buy {result.asset} on {result.buy_venue} "
                f"at VWAP ~{result.buy_price:.10g}; sell on {result.sell_venue} at VWAP ~{result.sell_price:.10g}; "
                f"quantity={result.quantity:.12g} ({result.notional_usd:.2f} USD notional). "
                f"Gross top-of-book edge={result.gross_edge:.2%}; order-book slippage={result.slippage:.2%}; "
                f"estimated fees={result.fees:.2%}; executable net edge={result.net_edge:.2%}. "
                "Pre-funded balances on both venues are required; no trade is submitted automatically."
            ),
            confidence=result.confidence, edge=result.net_edge, risk=result.risk,
            sources=tuple(result.sources), agent="DEPTH-VERIFIER",
            buy_venue=result.buy_venue, sell_venue=result.sell_venue,
            buy_price=result.buy_price, sell_price=result.sell_price,
            observed_at=result.observed_at, quantity=result.quantity,
            notional_usd=result.notional_usd, executable=True,
            verification=result.verification,
        )
        sent = self.alert_gateway.send(candidate)
        if sent:
            self.alerts_sent += 1
        return sent

    def scan_once(self) -> Opportunity | None:
        self.scans += 1
        self.last_alerts_sent = 0
        self._refresh()
        candidates = self._opportunities()
        self.last_opportunities = candidates[:25]
        for opportunity in candidates[:10]:
            if self._alert(opportunity):
                self.last_alerts_sent += 1
        return candidates[0] if candidates else None

    def snapshot(self) -> dict:
        return {
            "exchanges": list(self.exchange_names),
            "quote_currencies": list(self.quote_currencies),
            "market_universe": {name: len(symbols) for name, symbols in self._markets.items()},
            "symbols": len(self._quotes),
            "scans": self.scans,
            "alerts_sent": self.alerts_sent,
            "last_alerts_sent": self.last_alerts_sent,
            "verified_count": self.verified_count,
            "rejected_depth": self.rejected_depth,
            "orderbook_limit": self.orderbook_limit,
            "notional_usd": self.notional_usd,
            "max_quote_age_seconds": self.max_quote_age_seconds,
            "errors": dict(self.errors),
            "ccxt_available": ccxt is not None,
            "last_opportunities": [o.__dict__.copy() for o in self.last_opportunities],
        }
