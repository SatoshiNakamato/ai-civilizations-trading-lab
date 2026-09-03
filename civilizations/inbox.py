from __future__ import annotations

from dataclasses import dataclass, asdict
from collections import deque
from datetime import datetime, timezone


@dataclass
class Message:
    sender: str
    recipient: str
    text: str
    tick: int
    timestamp: str


class Inbox:
    """Local simulation message bus; it never sends messages externally."""

    def __init__(self, max_messages: int = 1000):
        self.messages = deque(maxlen=max_messages)

    def send(self, sender: str, recipient: str, text: str, tick: int) -> Message:
        msg = Message(sender, recipient, text, tick, datetime.now(timezone.utc).isoformat())
        self.messages.append(msg)
        return msg

    def for_recipient(self, recipient: str) -> list[dict]:
        return [asdict(m) for m in self.messages if m.recipient in (recipient, "ALL")]

    def snapshot(self) -> dict:
        return {"messages": len(self.messages)}
