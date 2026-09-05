"""Governed collective learning built on the agent communication bus.

The learning layer turns each agent's bounded observation into a peer-to-peer
exchange and periodically runs a lightweight adversarial debate. It keeps the
communication durable through AgentCommunicationBus while avoiding credentials,
arbitrary filesystem access, or unrestricted execution authority.
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
    """Coordinate bounded peer learning for the full civilization population."""

    def __init__(self, bus: AgentCommunicationBus, seed: int = 42):
        self.bus = bus
        self.rng = Random(seed)
        self._last_round: list[LearningExchange] = []
        self._last_debate: list[DebateExchange] = []

    def _peer(self, sender: str, agents: Sequence[str]) -> str:
        peers = [aid for aid in agents if aid != sender]
        if not peers:
            raise ValueError("collective learning requires at least two agents")
        return self.rng.choice(peers)

    def round(
        self,
        agents: Sequence[str],
        *,
        tick: int,
        evidence: Mapping[str, str],
    ) -> list[LearningExchange]:
        """Send one bounded observation from every agent to a peer."""
        agents = list(dict.fromkeys(agents))
        exchanges: list[LearningExchange] = []
        for sender in agents:
            body = str(evidence.get(sender, "")).strip()
            if not body:
                body = f"{sender} contributed no new evidence at tick {tick}."
            recipient = self._peer(sender, agents)
            message = self.bus.publish(
                sender,
                recipient,
                "research",
                body[: self.bus.config.max_message_bytes],
                ttl_seconds=7 * 86400,
            )
            exchanges.append(
                LearningExchange(
                    sender=sender,
                    recipient=recipient,
                    topic="research",
                    evidence=body,
                    confidence=0.7,
                    adopted=True,
                    message_id=message.message_id,
                )
            )
        self._last_round = exchanges
        return exchanges

    def debate(
        self,
        agents: Sequence[str],
        *,
        tick: int,
        topic: str,
    ) -> list[DebateExchange]:
        """Run a bounded adversarial challenge pass and persist each challenge."""
        agents = list(dict.fromkeys(agents))
        debates: list[DebateExchange] = []
        for sender in agents:
            recipient = self._peer(sender, agents)
            challenge = (
                f"Tick {tick}: challenge the strongest assumption in the "
                f"{topic} finding and request independent evidence."
            )
            message = self.bus.publish(sender, recipient, f"debate:{topic}", challenge)
            debates.append(
                DebateExchange(
                    sender=sender,
                    recipient=recipient,
                    topic=topic,
                    challenge=challenge,
                    confidence=0.65,
                    message_id=message.message_id,
                )
            )
        self._last_debate = debates
        return debates

    def snapshot(self) -> dict:
        """Return inspectable state without duplicating the durable message log."""
        return {
            "messages": 0,
            "last_round": [asdict(item) for item in self._last_round],
            "last_debate": [asdict(item) for item in self._last_debate],
            "communication_log": str(self.bus.log_path),
            "audit_log": str(self.bus.audit_path),
        }


__all__ = ["CollectiveLearning", "LearningExchange", "DebateExchange"]
