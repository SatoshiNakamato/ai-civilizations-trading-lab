from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class ExecutionConfig:
    max_order_quote: float = 25.0
    max_position_quote: float = 100.0
    max_daily_loss: float = 25.0
    max_daily_notional: float = 250.0
    slippage_bps: float = 100.0
    require_live_confirmation: bool = True

    @classmethod
    def from_env(cls):
        return cls(
            max_order_quote=float(os.getenv("LIVE_MAX_ORDER_QUOTE", "25")),
            max_position_quote=float(os.getenv("LIVE_MAX_POSITION_QUOTE", "100")),
            max_daily_loss=float(os.getenv("LIVE_MAX_DAILY_LOSS", "25")),
            max_daily_notional=float(os.getenv("LIVE_MAX_DAILY_NOTIONAL", "250")),
            slippage_bps=float(os.getenv("LIVE_MAX_SLIPPAGE_BPS", "100")),
            require_live_confirmation=os.getenv("LIVE_REQUIRE_CONFIRMATION", "1") == "1",
        )


class LiveExecutionEngine:
    """Guarded real-money order coordinator.

    This class deliberately does not store API credentials. The exchange adapter
    owns credential access. Every order gets a deterministic idempotency key and
    an append-only execution record so restarts cannot silently duplicate orders.
    """

    def __init__(self, adapter, audit_path="data/live_execution.jsonl", config=None, clock=time.time):
        self.adapter = adapter
        self.config = config or ExecutionConfig.from_env()
        self.audit_path = Path(audit_path)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock
        self.halted = False
        self._records = self._load_records()

    def _load_records(self):
        records = []
        if self.audit_path.exists():
            for line in self.audit_path.read_text().splitlines():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    def _append(self, event, **payload):
        record = {"event": event, "created_at": self.clock(), **payload}
        with self.audit_path.open("a") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
        self._records.append(record)
        return record

    def kill(self, reason="manual"):
        self.halted = True
        return self._append("kill_switch", reason=reason)

    def resume(self):
        self.halted = False
        return self._append("resume")

    def _day_records(self):
        now = self.clock()
        return [r for r in self._records if now - float(r.get("created_at", 0)) < 86400]

    def daily_notional(self):
        return sum(float(r.get("notional", 0)) for r in self._day_records() if r.get("event") == "order_submitted")

    def daily_realized_pnl(self):
        return sum(float(r.get("pnl", 0)) for r in self._day_records() if r.get("event") == "position_closed")

    def _idempotency_key(self, symbol, side, amount, client_ref):
        raw = f"{symbol}|{side}|{amount:.12f}|{client_ref}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def market_order(self, symbol: str, side: str, amount: float, estimated_price: float, client_ref: str) -> dict[str, Any]:
        if self.halted:
            raise RuntimeError("live execution kill switch is active")
        if self.config.require_live_confirmation and os.getenv("LIVE_TRADING_CONFIRMATION") != "I_UNDERSTAND_LIVE_RISK":
            raise RuntimeError("LIVE_TRADING_CONFIRMATION must equal I_UNDERSTAND_LIVE_RISK")
        if amount <= 0 or estimated_price <= 0:
            raise ValueError("amount and estimated_price must be positive")
        notional = amount * estimated_price
        if notional > self.config.max_order_quote:
            raise RuntimeError(f"order exceeds max quote size: {notional:.2f} > {self.config.max_order_quote:.2f}")
        if self.daily_notional() + notional > self.config.max_daily_notional:
            raise RuntimeError("daily live notional limit reached")
        if self.daily_realized_pnl() <= -self.config.max_daily_loss:
            self.kill("daily loss limit")
            raise RuntimeError("daily live loss limit reached")
        key = self._idempotency_key(symbol, side, amount, client_ref)
        prior = next((r for r in self._records if r.get("event") == "order_submitted" and r.get("idempotency_key") == key), None)
        if prior:
            return {"status": "already_submitted", **prior}
        self._append("order_intent", idempotency_key=key, symbol=symbol, side=side, amount=amount, estimated_price=estimated_price, notional=notional)
        result = self.adapter.create_market_order(symbol, side, amount)
        record = self._append("order_submitted", idempotency_key=key, symbol=symbol, side=side, amount=result.amount, price=result.price, notional=notional, order_id=result.order_id, status=result.status)
        return {"status": "submitted", **record}

    def reconcile_open_orders(self):
        out = []
        for record in self._records:
            if record.get("event") != "order_submitted" or not record.get("order_id"):
                continue
            try:
                state = self.adapter.fetch_order(record["order_id"], record["symbol"])
                out.append({"order_id": record["order_id"], "exchange_status": state.get("status"), "filled": state.get("filled"), "average": state.get("average")})
            except Exception as exc:
                out.append({"order_id": record["order_id"], "error": f"{type(exc).__name__}: {exc}"})
        return out

    def snapshot(self):
        return {"halted": self.halted, "daily_notional": self.daily_notional(), "daily_realized_pnl": self.daily_realized_pnl(), "records": len(self._records), "config": asdict(self.config)}
