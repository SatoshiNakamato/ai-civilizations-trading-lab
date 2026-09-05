"""Explicit execution boundary; paper mode by default."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OrderIntent:
    civilization_id: str
    symbol: str
    side: str
    quantity: float
    limit_price: float | None = None


class ExecutionAdapter(Protocol):
    def submit(self, order: OrderIntent) -> str: ...


class PaperExecution:
    def __init__(self) -> None:
        self.orders: list[OrderIntent] = []

    def submit(self, order: OrderIntent) -> str:
        if order.side not in {"buy", "sell"} or order.quantity <= 0:
            raise ValueError("invalid order intent")
        self.orders.append(order)
        return f"paper-{len(self.orders):08d}"


class GuardedExecution:
    def __init__(self, adapter: ExecutionAdapter, *, live_enabled: bool = False, max_quantity: float = 1.0) -> None:
        self.adapter = adapter
        self.live_enabled = live_enabled
        self.max_quantity = max_quantity

    def submit(self, order: OrderIntent) -> str:
        if not self.live_enabled:
            raise PermissionError("live execution is disabled")
        if order.quantity <= 0 or order.quantity > self.max_quantity:
            raise ValueError("order exceeds execution risk limit")
        return self.adapter.submit(order)
