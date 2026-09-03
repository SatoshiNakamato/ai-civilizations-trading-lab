from __future__ import annotations

from dataclasses import dataclass, asdict
from time import time


@dataclass
class Argument:
    agent_id: str
    thesis: str
    evidence: float
    confidence: float
    timestamp: float


class DebateChamber:
    """Records disagreement and ranks arguments by evidence and confidence."""
    def __init__(self):
        self.arguments: list[Argument] = []

    def submit(self, agent_id: str, thesis: str, evidence: float, confidence: float = 0.5):
        arg = Argument(agent_id, thesis, max(0.0, min(1.0, evidence)), max(0.0, min(1.0, confidence)), time())
        self.arguments.append(arg)
        return arg

    def rank(self, thesis: str | None = None, limit: int = 10):
        items = [a for a in self.arguments if thesis is None or a.thesis == thesis]
        return sorted(items, key=lambda a: a.evidence * 0.7 + a.confidence * 0.3, reverse=True)[:limit]

    def snapshot(self):
        return {"arguments": len(self.arguments), "top": [asdict(x) for x in self.rank()]}
