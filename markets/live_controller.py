from __future__ import annotations

import os
import time

from civilizations.autonomous_research import Opportunity
from markets.live_execution import LiveExecutionEngine


class LiveTradingController:
    """Connect ranked research opportunities to real, unlevered spot orders.

    The controller deliberately uses a small, explicit strategy: only the top
    ranked opportunity is eligible; positive 24h momentum produces a buy and
    negative momentum produces a sell only when the venue already reports a
    sufficient base-asset balance. No leverage or borrowing is used.
    """

    def __init__(self, executor: LiveExecutionEngine, quote_currency=None):
        self.executor = executor
        self.quote_currency = (quote_currency or os.getenv("LIVE_QUOTE_CURRENCY", "USDT")).upper()
        self.min_score = float(os.getenv("LIVE_MIN_RISK_ADJUSTED", "0.72"))
        self.order_quote = float(os.getenv("LIVE_ORDER_QUOTE", "10"))

    def select(self, opportunities: list[Opportunity]) -> Opportunity | None:
        eligible = [o for o in opportunities if o.risk_adjusted >= self.min_score]
        return max(eligible, key=lambda o: o.risk_adjusted, default=None)

    def execute_top(self, opportunities: list[Opportunity]) -> dict | None:
        opportunity = self.select(opportunities)
        if opportunity is None:
            return None
        h = opportunity.hypothesis
        symbol = self._symbol(h.ticker)
        observation = next((x for x in getattr(self.executor, "_market", []) if x.get("asset") == h.ticker), None)
        move = float(observation.get("change_24h", 0.0)) if observation else 0.0
        side = "buy" if move >= 0 else "sell"
        ticker = self.executor.exchange.fetch_ticker(symbol)
        mark = float(ticker.get("ask") or ticker.get("last") or ticker.get("bid") or 0.0)
        if mark <= 0:
            raise RuntimeError(f"no usable market price for {symbol}")
        amount = self.order_quote / mark
        intent = self.executor.new_intent(h.agent, symbol, side, amount, "market", reason=h.thesis)
        return self.executor.submit(intent)

    def _symbol(self, ticker: str) -> str:
        raw = ticker.upper().replace("/", "")
        if raw.endswith(self.quote_currency):
            base = raw[: -len(self.quote_currency)]
        else:
            base = raw
        return f"{base}/{self.quote_currency}"
