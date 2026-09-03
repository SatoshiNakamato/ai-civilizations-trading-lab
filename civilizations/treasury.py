from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TreasuryEvent:
    tick: int
    agent_id: str
    kind: str
    amount: float
    reason: str


@dataclass
class Treasury:
    """Simulation-only economy. No signing, transfers, or private keys."""
    public_address: str | None = None
    balance: float = 100_000.0
    reserved: float = 0.0
    events: List[TreasuryEvent] = field(default_factory=list)
    contributions: Dict[str, float] = field(default_factory=dict)

    def contribute(self, agent_id: str, amount: float, tick: int, reason: str) -> bool:
        if amount <= 0 or amount > self.balance - self.reserved:
            return False
        self.balance -= amount
        self.contributions[agent_id] = self.contributions.get(agent_id, 0.0) + amount
        self.events.append(TreasuryEvent(tick, agent_id, "contribution", amount, reason))
        return True

    def reward(self, agent_id: str, amount: float, tick: int, reason: str) -> bool:
        if amount <= 0 or amount > self.balance:
            return False
        self.balance -= amount
        self.events.append(TreasuryEvent(tick, agent_id, "reward", amount, reason))
        return True

    def reserve(self, agent_id: str, amount: float, tick: int, reason: str) -> bool:
        if amount <= 0 or amount > self.balance - self.reserved:
            return False
        self.reserved += amount
        self.events.append(TreasuryEvent(tick, agent_id, "reserve", amount, reason))
        return True

    def snapshot(self) -> dict:
        return {
            "public_address": self.public_address,
            "balance": round(self.balance, 2),
            "reserved": round(self.reserved, 2),
            "events": len(self.events),
            "contributions": {k: round(v, 2) for k, v in self.contributions.items()},
        }
