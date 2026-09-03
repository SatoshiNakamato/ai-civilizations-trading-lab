from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Knowledge:
    topic: str
    claim: str
    author: str
    evidence: float
    generation: int
    confirmations: int = 0
    challenges: int = 0


@dataclass
class Conversation:
    generation: int
    speaker: str
    listener: str
    topic: str
    message: str
    useful: float


@dataclass
class Society:
    """Shared social memory for the simulated civilization."""

    knowledge: Dict[str, Knowledge] = field(default_factory=dict)
    conversations: List[Conversation] = field(default_factory=list)
    relationships: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def record_knowledge(
        self,
        topic: str,
        claim: str,
        author: str,
        evidence: float,
        generation: int,
    ) -> Knowledge:
        evidence = max(0.0, min(1.0, evidence))
        existing = self.knowledge.get(topic)
        if existing is None or evidence > existing.evidence:
            item = Knowledge(topic, claim, author, evidence, generation)
            self.knowledge[topic] = item
            return item
        existing.challenges += 1
        return existing

    def confirm(self, topic: str) -> None:
        if topic in self.knowledge:
            self.knowledge[topic].confirmations += 1

    def challenge(self, topic: str) -> None:
        if topic in self.knowledge:
            self.knowledge[topic].challenges += 1

    def talk(
        self,
        generation: int,
        speaker: str,
        listener: str,
        topic: str,
        message: str,
        useful: float,
    ) -> Conversation:
        useful = max(0.0, min(1.0, useful))
        event = Conversation(generation, speaker, listener, topic, message, useful)
        self.conversations.append(event)
        self.conversations = self.conversations[-1000:]
        self.relationships.setdefault(speaker, {})[listener] = useful
        return event

    def search(self, topic: str) -> Knowledge | None:
        return self.knowledge.get(topic)

    def snapshot(self) -> dict:
        return {
            "knowledge_count": len(self.knowledge),
            "conversation_count": len(self.conversations),
            "knowledge": [
                {
                    "topic": k.topic,
                    "author": k.author,
                    "evidence": round(k.evidence, 4),
                    "confirmations": k.confirmations,
                    "challenges": k.challenges,
                }
                for k in self.knowledge.values()
            ],
        }
