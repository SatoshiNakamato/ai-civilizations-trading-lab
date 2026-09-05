"""Governed collective learning rounds for the civilization.

This layer connects the durable communication bus to the existing civilization
learning model. It deliberately does not grant agents credentials, arbitrary
filesystem access, or direct execution authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from random import Random
from typing import Iterable

from .agent_communication import AgentCommunicationBus


@dataclass(frozen=True)
class LearningExchange:
    tick: int
    sender: str
    recipient: str
    topic: str
    message_id: str
    adopted: bool
    confidence: float


class CollectiveLearning:
    """Turn agent observations into governed peer-to-peer learning."""

    def __init__(self, bus: AgentCommunicationBus | None = None, seed: int = 42) -> None:
        self.bus = bus or AgentCommunicationBus()
        self.rng = Random(seed)
        self.exchanges: list[LearningExchange] = []

    def round(self, agents: Iterable[str], *, tick: int, evidence: dict[str, str]) -> list[LearningExchange]:
        ids = list(dict.fromkeys(agents))
        if len(ids) < 2:
            return []
        results: list[LearningExchange] = []
        for sender in ids:
            finding = str(evidence.get(sender, ""))[:800].strip()
            if not finding:
                continue
            # Each agent teaches one peer; bounded fan-out prevents a 100-agent
            # round from becoming an uncontrolled message storm.
            offset = 1 + self.rng.randrange(len(ids) - 1)
            recipient = ids[(ids.index(sender) + offset) % len(ids)]
            topic = f"research:{tick}"
            msg = self.bus.publish(sender, recipient, topic, finding, ttl_seconds=7 * 86400)
            confidence = 0.5 + self.rng.random() * 0.4
            adopted = confidence >= 0.65
            results.append(LearningExchange(tick, sender, recipient, topic, msg.message_id, adopted, round(confidence, 3)))
        self.exchanges.extend(results)
        self.exchanges = self.exchanges[-500:]
        return results

    def debate(self, agents: Iterable[str], *, tick: int, topic: str) -> list[dict[str, object]]:
        ids = list(dict.fromkeys(agents))
        if len(ids) < 2:
            return []
        rounds: list[dict[str, object]] = []
        for idx, sender in enumerate(ids):
            recipient = ids[(idx + 1) % len(ids)]
            objection = f"Challenge evidence for {topic}: identify assumptions, missing data, and failure modes."
            msg = self.bus.publish(sender, recipient, f"debate:{tick}", objection, ttl_seconds=86400)
            rounds.append({"sender": sender, "recipient": recipient, "message_id": msg.message_id, "topic": topic})
        return rounds

    def snapshot(self) -> dict[str, object]:
        return {
            "messages": len(self.exchanges),
            "recent": [asdict(x) for x in self.exchanges[-20:]],
            "bus": {"log": str(self.bus.log_path), "audit": str(self.bus.audit_path)},
        }


__all__ = ["CollectiveLearning", "LearningExchange"]
