from __future__ import annotations

from dataclasses import dataclass
from time import time


@dataclass
class KnowledgeTransfer:
    sender: str
    receiver: str
    topic: str
    evidence_score: float
    created_at: float


class KnowledgeExchange:
    def __init__(self):
        self.transfers: list[KnowledgeTransfer] = []

    def share(self, sender: str, receiver: str, topic: str, evidence_score: float):
        item = KnowledgeTransfer(sender, receiver, topic, max(0.0, min(1.0, evidence_score)), time())
        self.transfers.append(item)
        return item

    def recent(self, limit: int = 20):
        return self.transfers[-limit:]

    def snapshot(self):
        return {"transfers": len(self.transfers), "recent": [x.__dict__ for x in self.recent()]}
