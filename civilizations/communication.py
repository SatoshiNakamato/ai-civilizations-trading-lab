from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Message:
    sender: str
    recipient: str
    kind: str
    content: str
    tick: int


class Memory:
    def __init__(self, limit: int = 100):
        self.limit = limit
        self.messages: List[Message] = []

    def remember(self, message: Message) -> None:
        self.messages.append(message)
        self.messages = self.messages[-self.limit :]

    def recent(self, agent_id: str, n: int = 10) -> List[Message]:
        return [m for m in self.messages if m.recipient == agent_id or m.sender == agent_id][-n:]


class CommunicationNetwork:
    """A bounded in-process social network for research agents."""

    def __init__(self):
        self.memory = Memory()
        self.reputations: Dict[str, float] = {}

    def send(self, sender: str, recipient: str, kind: str, content: str, tick: int) -> Message:
        message = Message(sender, recipient, kind, content, tick)
        self.memory.remember(message)
        return message

    def update_reputation(self, agent_id: str, delta: float) -> None:
        self.reputations[agent_id] = max(-1.0, min(1.0, self.reputations.get(agent_id, 0.0) + delta))
