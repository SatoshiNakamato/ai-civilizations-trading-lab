from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: str
    amount: float
    price: float | None
    status: str
    raw: dict[str, Any]


class CcxtExchangeAdapter:
    """Real exchange adapter using CCXT credentials supplied only by environment."""

    def __init__(self, exchange_id: str | None = None):
        self.exchange_id = exchange_id or os.getenv("TRADING_EXCHANGE", "coinbase")
        self._exchange = None

    @property
    def exchange(self):
        if self._exchange is None:
            import ccxt
            exchange_cls = getattr(ccxt, self.exchange_id, None)
            if exchange_cls is None:
                raise RuntimeError(f"Unsupported CCXT exchange: {self.exchange_id}")
            key = os.getenv("TRADING_API_KEY", "").strip()
            secret = os.getenv("TRADING_API_SECRET", "").strip()
            password = os.getenv("TRADING_API_PASSWORD", "").strip()
            if not key or not secret:
                raise RuntimeError("TRADING_API_KEY and TRADING_API_SECRET are required for live trading")
            config = {"apiKey": key, "secret": secret, "enableRateLimit": True}
            if password:
                config["password"] = password
            self._exchange = exchange_cls(config)
        return self._exchange

    def markets(self):
        return self.exchange.load_markets()

    def balance(self):
        return self.exchange.fetch_balance()

    def ticker(self, symbol: str):
        return self.exchange.fetch_ticker(symbol)

    def create_market_order(self, symbol: str, side: str, amount: float) -> OrderResult:
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        if amount <= 0:
            raise ValueError("amount must be positive")
        raw = self.exchange.create_order(symbol, "market", side, amount)
        return OrderResult(
            order_id=str(raw.get("id", "")),
            symbol=symbol,
            side=side,
            amount=float(raw.get("amount") or amount),
            price=float(raw["average"]) if raw.get("average") is not None else None,
            status=str(raw.get("status", "open")),
            raw=raw,
        )

    def cancel_order(self, order_id: str, symbol: str):
        return self.exchange.cancel_order(order_id, symbol)

    def fetch_order(self, order_id: str, symbol: str):
        return self.exchange.fetch_order(order_id, symbol)
