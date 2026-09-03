from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Conversation:
    conversation_id: str
    participants: List[str]
    topic: str
    transcript: List[str] = field(default_factory=list)
    tick: int = 0


@dataclass
class ResearchRecord:
    researcher: str
    question: str
    finding: str
    confidence: float
    tick: int


class CivilizationWorld:
    """Persistent social layer: conversations, shared knowledge and research."""

    def __init__(self, memory_limit: int = 500):
        self.memory_limit = memory_limit
        self.conversations: List[Conversation] = []
        self.knowledge: Dict[str, str] = {}
        self.research: List[ResearchRecord] = []
        self.relationships: Dict[tuple[str, str], float] = {}

    def talk(self, conversation_id: str, participants: List[str], topic: str, tick: int) -> Conversation:
        conversation = Conversation(conversation_id, participants[:], topic, tick=tick)
        self.conversations.append(conversation)
        self.conversations = self.conversations[-self.memory_limit:]
        return conversation

    def say(self, conversation: Conversation, speaker: str, message: str) -> None:
        conversation.transcript.append(f"{speaker}: {message}")
        conversation.transcript = conversation.transcript[-50:]

    def learn(self, key: str, finding: str) -> None:
        self.knowledge[key] = finding
        if len(self.knowledge) > self.memory_limit:
            oldest = next(iter(self.knowledge))
            del self.knowledge[oldest]

    def record_research(self, record: ResearchRecord) -> None:
        self.research.append(record)
        self.research = self.research[-self.memory_limit:]
        self.learn(record.question, record.finding)

    def strengthen_relationship(self, a: str, b: str, delta: float) -> None:
        key = tuple(sorted((a, b)))
        self.relationships[key] = max(-1.0, min(1.0, self.relationships.get(key, 0.0) + delta))
