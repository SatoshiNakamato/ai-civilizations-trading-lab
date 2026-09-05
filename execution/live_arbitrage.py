from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from execution.ccxt_adapter import CcxtExchangeAdapter


@dataclass(frozen=True)
class LiveArbitrageConfig:
    max_quote: float = 25.0
    min_net_edge: float = 0.0075
    max_quote_age: float = 5.0
    require_confirmation: bool = True

    @classmethod
    def from_env(cls):
        return cls(
            max_quote=float(os.getenv("LIVE_ARB_MAX_QUOTE", "25")),
            min_net_edge=float(os.getenv("LIVE_ARB_MIN_NET_EDGE", "0.0075")),
            max_quote_age=float(os.getenv("LIVE_ARB_MAX_QUOTE_AGE", "5")),
            require_confirmation=os.getenv("LIVE_ARB_REQUIRE_CONFIRMATION", "1") == "1",
        )


@dataclass(frozen=True)
class LiveArbitrageResult:
    status: str
    asset: str
    quantity: float
    buy_venue: str
    sell_venue: str
    buy_order_id: str = ""
    sell_order_id: str = ""
    buy_price: float = 0.0
    sell_price: float = 0.0
    estimated_net_edge: float = 0.0
    error: str = ""
    created_at: float = 0.0


class LiveArbitrageExecutor:
    """Execute a validated cross-venue opportunity using two isolated accounts.

    This is intentionally opt-in. Both legs use the same quantity and are
    constrained by a small notional limit. If the second leg fails, the result
    is marked ``partial`` so the operator can reconcile the remaining exposure.
    """

    def __init__(self, buy_adapter=None, sell_adapter=None, config=None, audit_path="data/live_arbitrage.jsonl", clock=time.time):
        self.config = config or LiveArbitrageConfig.from_env()
        self.buy = buy_adapter or CcxtExchangeAdapter(os.getenv("ARBITRAGE_BUY_EXCHANGE", ""), "ARBITRAGE_BUY")
        self.sell = sell_adapter or CcxtExchangeAdapter(os.getenv("ARBITRAGE_SELL_EXCHANGE", ""), "ARBITRAGE_SELL")
        self.audit_path = Path(audit_path)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock

    def enabled(self) -> bool:
        return os.getenv("LIVE_ARBITRAGE", "0") == "1"

    def _audit(self, result: LiveArbitrageResult):
        with self.audit_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(result), sort_keys=True) + "\n")

    def execute(self, opportunity, quantity: float | None = None) -> LiveArbitrageResult:
        if not self.enabled():
            raise RuntimeError("LIVE_ARBITRAGE=1 is required for live arbitrage")
        if self.config.require_confirmation and os.getenv("LIVE_TRADING_CONFIRMATION") != "I_UNDERSTAND_LIVE_RISK":
            raise RuntimeError("LIVE_TRADING_CONFIRMATION must equal I_UNDERSTAND_LIVE_RISK")
        if opportunity.status != "validated":
            raise RuntimeError("arbitrage opportunity is not validated")
        if opportunity.net_edge < self.config.min_net_edge:
            raise RuntimeError(f"live arbitrage edge below threshold: {opportunity.net_edge:.3%}")

        buy_venue = opportunity.buy_venue
        sell_venue = opportunity.sell_venue
        if not buy_venue or not sell_venue or buy_venue == sell_venue:
            raise RuntimeError("arbitrage opportunity has invalid venue route")
        qty = float(quantity or os.getenv("LIVE_ARB_QUANTITY", "0.001"))
        if qty <= 0:
            raise ValueError("live arbitrage quantity must be positive")
        reference = max(float(opportunity.buy_price), 0.0) * qty
        if reference > self.config.max_quote:
            raise RuntimeError(f"live arbitrage notional exceeds limit: {reference:.2f} > {self.config.max_quote:.2f}")

        symbol = self._ccxt_symbol(opportunity.asset)
        buy_ticker = self.buy.ticker(symbol)
        sell_ticker = self.sell.ticker(symbol)
        buy_price = float(buy_ticker.get("ask") or buy_ticker.get("last") or 0)
        sell_price = float(sell_ticker.get("bid") or sell_ticker.get("last") or 0)
        if buy_price <= 0 or sell_price <= 0:
            raise RuntimeError("live venues returned unusable prices")
        live_edge = (sell_price - buy_price) / buy_price
        if live_edge < self.config.min_net_edge:
            raise RuntimeError(f"live arbitrage edge disappeared: {live_edge:.3%}")

        now = self.clock()
        for label, ticker in (("buy", buy_ticker), ("sell", sell_ticker)):
            ts = ticker.get("timestamp")
            if ts is not None and now - float(ts) / 1000.0 > self.config.max_quote_age:
                raise RuntimeError(f"{label} quote is stale")

        buy_order = self.buy.create_market_order(symbol, "buy", qty)
        try:
            sell_order = self.sell.create_market_order(symbol, "sell", qty)
        except Exception as exc:
            result = LiveArbitrageResult("partial", opportunity.asset, qty, buy_venue, sell_venue, buy_order.order_id, "", buy_order.price or buy_price, 0.0, live_edge, f"second leg failed: {type(exc).__name__}: {exc}", now)
            self._audit(result)
            raise RuntimeError(result.error) from exc

        result = LiveArbitrageResult("executed", opportunity.asset, qty, buy_venue, sell_venue, buy_order.order_id, sell_order.order_id, buy_order.price or buy_price, sell_order.price or sell_price, live_edge, "", now)
        self._audit(result)
        return result

    @staticmethod
    def _ccxt_symbol(asset: str) -> str:
        clean = str(asset).upper().replace("-USD", "").replace("/USD", "")
        return f"{clean}/USDT"
