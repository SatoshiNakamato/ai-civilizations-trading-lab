"""Governed collective learning and evolution built on the agent communication bus.

The learning layer turns bounded observations into peer-to-peer research exchange,
then performs synthesis, adversarial review, confidence scoring, adoption, and
cycle history. It never grants agents credentials, arbitrary filesystem access,
or unrestricted execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from random import Random
from typing import Mapping, Sequence

from .agent_communication import AgentCommunicationBus


@dataclass(frozen=True, slots=True)
class LearningExchange:
    sender: str
    recipient: str
    topic: str
    evidence: str
    confidence: float
    adopted: bool = True
    message_id: str | None = None


@dataclass(frozen=True, slots=True)
class DebateExchange:
    sender: str
    recipient: str
    topic: str
    challenge: str
    confidence: float
    message_id: str | None = None


class CollectiveLearning:
    """Coordinate a bounded research -> debate -> adoption evolution loop.

    Communication limits are resource controls, not civilization-fatal errors.
    When the message governor is exhausted, the learning cycle records the
    throttling event and continues with the evidence already available.
    """

    def __init__(self, bus: AgentCommunicationBus, seed: int = 42):
        self.bus = bus
        self.rng = Random(seed)
        self._last_round: list[LearningExchange] = []
        self._last_debate: list[DebateExchange] = []
        self._last_synthesis: dict = {}
        self._last_adoption: list[dict] = []
        self._cycle_history: list[dict] = []
        self._throttled_messages = 0
        self._last_quota_event: dict | None = None

    def _peer(self, sender: str, agents: Sequence[str]) -> str:
        peers = [aid for aid in agents if aid != sender]
        if not peers:
            raise ValueError("collective learning requires at least two agents")
        return self.rng.choice(peers)

    def _safe_publish(self, sender: str, recipient: str, topic: str, body: str, *, ttl_seconds: int | None = None):
        """Publish when capacity exists; throttle instead of crashing the loop."""
        try:
            return self.bus.publish(sender, recipient, topic, body, ttl_seconds=ttl_seconds)
        except RuntimeError as exc:
            if str(exc) != "communication message quota exhausted":
                raise
            self._throttled_messages += 1
            self._last_quota_event = {
                "type": "communication_quota_exhausted",
                "sender": sender,
                "recipient": recipient,
                "topic": topic,
                "action": "throttled",
            }
            return None

    def round(self, agents: Sequence[str], *, tick: int, evidence: Mapping[str, str]) -> list[LearningExchange]:
        """Run the research-sharing stage: every agent contributes when capacity allows."""
        agents = list(dict.fromkeys(agents))
        exchanges: list[LearningExchange] = []
        for sender in agents:
            body = str(evidence.get(sender, "")).strip()
            if not body:
                body = f"{sender} contributed no new evidence at tick {tick}."
            recipient = self._peer(sender, agents)
            message = self._safe_publish(
                sender,
                recipient,
                "research",
                body[: self.bus.config.max_message_bytes],
                ttl_seconds=7 * 86400,
            )
            if message is not None:
                exchanges.append(LearningExchange(sender, recipient, "research", body, 0.7, True, message.message_id))
        confidence = sum(x.confidence for x in exchanges) / max(1, len(exchanges))
        self._last_synthesis = {
            "tick": tick,
            "contributors": len(exchanges),
            "topics": sorted({x.topic for x in exchanges}),
            "mean_confidence": round(confidence, 4),
            "independent_sources": len({x.sender for x in exchanges}),
            "communication_throttled": self._last_quota_event is not None,
        }
        self._last_round = exchanges
        self._score_adoption(exchanges, tick=tick)
        self._cycle_history.append({
            "tick": tick,
            "agents": len(agents),
            "research_exchanges": len(exchanges),
            "debates": 0,
            "adopted": sum(1 for item in self._last_adoption if item["adopted"]),
            "rejected": sum(1 for item in self._last_adoption if not item["adopted"]),
            "synthesis": dict(self._last_synthesis),
            "communication_throttled": self._last_quota_event is not None,
        })
        self._cycle_history = self._cycle_history[-100:]
        return exchanges

    def _score_adoption(self, exchanges: Sequence[LearningExchange], *, tick: int) -> None:
        """Score knowledge adoption rather than blindly copying every claim."""
        decisions: list[dict] = []
        for item in exchanges:
            novelty = 0.75 if item.evidence else 0.0
            support = min(1.0, item.confidence + 0.1)
            score = round((novelty * 0.4) + (support * 0.6), 4)
            decisions.append({
                "tick": tick,
                "agent": item.recipient,
                "source": item.sender,
                "score": score,
                "adopted": score >= 0.6,
                "reason": "evidence and confidence exceeded adoption threshold" if score >= 0.6 else "insufficient support",
            })
        self._last_adoption = decisions

    def debate(self, agents: Sequence[str], *, tick: int, topic: str) -> list[DebateExchange]:
        """Run a bounded adversarial challenge pass against the latest synthesis."""
        agents = list(dict.fromkeys(agents))
        debates: list[DebateExchange] = []
        synthesis = self._last_synthesis or {"contributors": 0, "mean_confidence": 0.0}
        for sender in agents:
            recipient = self._peer(sender, agents)
            challenge = (
                f"Tick {tick}: challenge the {topic} synthesis; it has "
                f"{synthesis.get('contributors', 0)} contributors and mean confidence "
                f"{synthesis.get('mean_confidence', 0.0):.3f}. Request counter-evidence or a reproducible test."
            )
            message = self._safe_publish(sender, recipient, f"debate:{topic}", challenge)
            if message is not None:
                debates.append(DebateExchange(sender, recipient, topic, challenge, 0.65, message.message_id))
        self._last_debate = debates
        for cycle in reversed(self._cycle_history):
            if cycle["tick"] == tick:
                cycle["debates"] = len(debates)
                break
        return debates

    def complete_cycle(self, agents: Sequence[str], *, tick: int, evidence: Mapping[str, str], topic: str = "collective research review") -> dict:
        """Execute research -> synthesis -> debate -> adoption as one cycle."""
        self.round(agents, tick=tick, evidence=evidence)
        debates = self.debate(agents, tick=tick, topic=topic)
        adopted = sum(1 for item in self._last_adoption if item["adopted"])
        cycle = {
            "tick": tick,
            "agents": len(list(dict.fromkeys(agents))),
            "research_exchanges": len(self._last_round),
            "debates": len(debates),
            "adopted": adopted,
            "rejected": len(self._last_adoption) - adopted,
            "synthesis": dict(self._last_synthesis),
            "communication_throttled": self._last_quota_event is not None,
            "throttled_messages": self._throttled_messages,
        }
        if self._cycle_history and self._cycle_history[-1]["tick"] == tick:
            self._cycle_history[-1] = cycle
        else:
            self._cycle_history.append(cycle)
        self._cycle_history = self._cycle_history[-100:]
        return cycle

    def snapshot(self) -> dict:
        """Return inspectable state without duplicating the durable message log."""
        return {
            "messages": 0,
            "last_round": [asdict(item) for item in self._last_round],
            "last_debate": [asdict(item) for item in self._last_debate],
            "last_synthesis": dict(self._last_synthesis),
            "last_adoption": list(self._last_adoption),
            "cycle_history": list(self._cycle_history),
            "communication_log": str(self.bus.log_path),
            "audit_log": str(self.bus.audit_path),
            "throttled_messages": self._throttled_messages,
            "last_quota_event": dict(self._last_quota_event) if self._last_quota_event else None,
        }


__all__ = ["CollectiveLearning", "LearningExchange", "DebateExchange"]
