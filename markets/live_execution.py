from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os
import time
import uuid


@dataclass(frozen=True)
class LiveOrderIntent:
    intent_id: str
    agent: str
    symbol: str
    side: str
    amount: float
    order_type: str = "market"
    limit_price: float | None = None
    reason: str = ""
    created_at: float = 0.0


class LiveExecutionError(RuntimeError):
    pass


class LiveExecutionEngine:
    """Real exchange execution through CCXT.

    This engine has no paper/simulation fallback. It submits real orders only
    when LIVE_TRADING=1 and the kill switch is explicitly clear. Credentials
    are read from the process environment and never written to the ledger.
    """

    def __init__(self, ledger_path="data/live_orders.jsonl", exchange=None):
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.exchange = exchange or self._build_exchange()
        self.max_order_notional = float(os.getenv("LIVE_MAX_ORDER_NOTIONAL", "50"))
        self.max_total_notional = float(os.getenv("LIVE_MAX_TOTAL_NOTIONAL", "200"))
        self._seen = self._load_intents()

    @staticmethod
    def _build_exchange():
        import ccxt

        name = os.getenv("LIVE_EXCHANGE", "").strip().lower()
        if not name:
            raise LiveExecutionError("LIVE_EXCHANGE is required for live trading")
        api_key = os.getenv("LIVE_API_KEY", "").strip()
        secret = os.getenv("LIVE_API_SECRET", "").strip()
        if not api_key or not secret:
            raise LiveExecutionError("LIVE_API_KEY and LIVE_API_SECRET are required")
        cls = getattr(ccxt, name, None)
        if cls is None:
            raise LiveExecutionError(f"unsupported CCXT exchange: {name}")
        params = {"apiKey": api_key, "secret": secret}
        password = os.getenv("LIVE_API_PASSWORD", "").strip()
        if password:
            params["password"] = password
        exchange = cls(params)
        if hasattr(exchange, "enableRateLimit"):
            exchange.enableRateLimit = True
        return exchange

    @classmethod
    def from_env(cls, ledger_path="data/live_orders.jsonl"):
        if os.getenv("LIVE_TRADING") != "1":
            raise LiveExecutionError("LIVE_TRADING=1 is required; refusing to execute live orders")
        if os.getenv("LIVE_TRADING_KILL_SWITCH", "0") == "1":
            raise LiveExecutionError("live trading kill switch is active")
        return cls(ledger_path=ledger_path)

    def preflight(self, symbol: str | None = None) -> dict:
        if os.getenv("LIVE_TRADING") != "1":
            raise LiveExecutionError("LIVE_TRADING=1 is required")
        if os.getenv("LIVE_TRADING_KILL_SWITCH", "0") == "1":
            raise LiveExecutionError("live trading kill switch is active")
        if hasattr(self.exchange, "check_required_credentials") and not self.exchange.check_required_credentials():
            raise LiveExecutionError("exchange credentials are incomplete")
        balance = self.exchange.fetch_balance()
        result = {"exchange": self.exchange.id, "live": True, "timestamp": time.time()}
        if symbol:
            result["ticker"] = self.exchange.fetch_ticker(symbol)
        result["balance_available"] = balance.get("free", {})
        return result

    def submit(self, intent: LiveOrderIntent) -> dict:
        if intent.intent_id in self._seen:
            return self._seen[intent.intent_id]
        self._guard(intent)
        params = {}
        client_id = f"civ-{intent.intent_id[:20]}"
        # CCXT exposes clientOrderId through params on exchanges that support it.
        params["clientOrderId"] = client_id
        try:
            order = self.exchange.create_order(
                intent.symbol,
                intent.order_type,
                intent.side.lower(),
                float(intent.amount),
                intent.limit_price,
                params,
            )
        except Exception as exc:
            event = {"intent": asdict(intent), "status": "rejected", "error": f"{type(exc).__name__}: {exc}", "created_at": time.time()}
            self._write(event)
            raise LiveExecutionError(event["error"]) from exc
        event = {"intent": asdict(intent), "status": "submitted", "order": order, "created_at": time.time()}
        self._write(event)
        self._seen[intent.intent_id] = event
        return event

    def reconcile(self, order_id: str, symbol: str) -> dict:
        try:
            order = self.exchange.fetch_order(order_id, symbol)
        except Exception as exc:
            raise LiveExecutionError(f"order reconciliation failed: {type(exc).__name__}: {exc}") from exc
        event = {"status": "reconciled", "order": order, "created_at": time.time()}
        self._write(event)
        return event

    def cancel(self, order_id: str, symbol: str) -> dict:
        try:
            order = self.exchange.cancel_order(order_id, symbol)
        except Exception as exc:
            raise LiveExecutionError(f"order cancellation failed: {type(exc).__name__}: {exc}") from exc
        event = {"status": "cancelled", "order": order, "created_at": time.time()}
        self._write(event)
        return event

    def _guard(self, intent: LiveOrderIntent):
        if os.getenv("LIVE_TRADING") != "1":
            raise LiveExecutionError("LIVE_TRADING=1 is required")
        if os.getenv("LIVE_TRADING_KILL_SWITCH", "0") == "1":
            raise LiveExecutionError("live trading kill switch is active")
        if intent.side.lower() not in {"buy", "sell"}:
            raise LiveExecutionError("order side must be buy or sell")
        if intent.order_type.lower() not in {"market", "limit"}:
            raise LiveExecutionError("unsupported order type")
        if intent.amount <= 0:
            raise LiveExecutionError("order amount must be positive")
        if intent.order_type.lower() == "limit" and (intent.limit_price is None or intent.limit_price <= 0):
            raise LiveExecutionError("limit orders require a positive limit_price")
        notional = float(intent.amount) * float(intent.limit_price or 0)
        if intent.order_type.lower() == "market":
            ticker = self.exchange.fetch_ticker(intent.symbol)
            mark = float(ticker.get("last") or ticker.get("ask") or ticker.get("bid") or 0)
            notional = float(intent.amount) * mark
        if notional > self.max_order_notional:
            raise LiveExecutionError(f"live order notional {notional:.8f} exceeds max {self.max_order_notional:.8f}")
        open_notional = self._open_notional()
        if open_notional + notional > self.max_total_notional:
            raise LiveExecutionError(f"live exposure {open_notional + notional:.8f} exceeds max {self.max_total_notional:.8f}")

    def _open_notional(self) -> float:
        total = 0.0
        for event in self._iter_ledger():
            if event.get("status") != "submitted":
                continue
            order = event.get("order") or {}
            if str(order.get("status", "")).lower() in {"closed", "canceled", "cancelled", "rejected"}:
                continue
            total += float(order.get("cost") or 0.0)
        return total

    def _load_intents(self):
        seen = {}
        for event in self._iter_ledger():
            intent = event.get("intent") or {}
            if event.get("status") == "submitted" and intent.get("intent_id"):
                seen[intent["intent_id"]] = event
        return seen

    def _iter_ledger(self):
        try:
            with self.ledger_path.open(encoding="utf-8") as handle:
                for line in handle:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return

    def _write(self, event):
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    @staticmethod
    def new_intent(agent, symbol, side, amount, order_type="market", limit_price=None, reason=""):
        return LiveOrderIntent(str(uuid.uuid4()), agent, symbol.upper(), side.lower(), float(amount), order_type.lower(), limit_price, reason, time.time())
