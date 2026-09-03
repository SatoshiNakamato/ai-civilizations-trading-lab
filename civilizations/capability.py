from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Capability:
    score: float = 100.0
    research: float = 0.0
    validation: float = 0.0
    collaboration: float = 0.0
    trials: int = 0


class CapabilityLedger:
    """Capability is earned from measured outcomes rather than a fixed IQ."""
    def __init__(self):
        self.agents: dict[str, Capability] = {}

    def record(self, agent_id: str, validation_score: float, evidence: float = 1.0, collaboration: float = 0.0):
        c = self.agents.setdefault(agent_id, Capability())
        c.trials += 1
        c.validation = (c.validation * (c.trials - 1) + validation_score) / c.trials
        c.research = (c.research * (c.trials - 1) + evidence) / c.trials
        c.collaboration = (c.collaboration * (c.trials - 1) + collaboration) / c.trials
        delta = max(-1.0, min(1.0, validation_score)) * 0.5 + evidence * 0.05 + collaboration * 0.05
        c.score = max(0.0, c.score + delta)
        return c

    def rank(self, limit=10):
        return sorted(self.agents.items(), key=lambda kv: kv[1].score, reverse=True)[:limit]

    def snapshot(self):
        return {aid: vars(cap).copy() for aid, cap in self.agents.items()}
