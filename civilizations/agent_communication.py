"""Governed inter-agent communication for the civilization runtime.

Agents can exchange research, hypotheses, objections, and memory references
through a durable message bus. The bus is deliberately narrower than a raw
filesystem: every message is validated, quota-limited, auditable, and scoped
to the civilization workspace. No credentials are exposed to agents.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
import re
import time
from pathlib import Path

_SAFE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


@dataclass(frozen=True)
class CommunicationConfig:
    root: Path = Path("data/communication")
    max_message_bytes: int = 16_000
    max_messages: int = 10_000
    max_recipients: int = 100

    @classmethod
    def from_env(cls) -> "CommunicationConfig":
        return cls(
            root=Path(os.getenv("AEON_COMMUNICATION_ROOT", "data/communication")),
            max_message_bytes=max(1024, int(os.getenv("AEON_COMM_MAX_MESSAGE_BYTES", "16000"))),
            max_messages=max(100, int(os.getenv("AEON_COMM_MAX_MESSAGES", "10000"))),
            max_recipients=max(1, int(os.getenv("AEON_COMM_MAX_RECIPIENTS", "100"))),
        )


@dataclass(frozen=True)
class AgentMessage:
    message_id: str
    sender: str
    recipient: str
    topic: str
    body: str
    created_at: float
    reply_to: str | None = None
    ttl_seconds: int | None = None


class AgentCommunicationBus:
    """A governed mailbox shared by agents.

    The bus is intentionally capability-oriented: agents get message
    operations, not arbitrary filesystem access. Messages are JSONL records so
    the civilization can inspect and replay its communication history.

    ``max_messages`` is a bounded active-segment quota. When the segment fills,
    it is rotated into an immutable archive instead of crashing the civilization.
    This preserves history while preventing unbounded growth of the hot log.
    """

    def __init__(self, config: CommunicationConfig | None = None):
        self.config = config or CommunicationConfig.from_env()
        self.root = self.config.root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.archive_root = self.root / "archive"
        self.archive_root.mkdir(parents=True, exist_ok=True)
        self.log_path = self.root / "messages.jsonl"
        self.audit_path = self.root / "communication_audit.jsonl"

    @staticmethod
    def _agent(value: str) -> str:
        if not isinstance(value, str) or not _SAFE.fullmatch(value):
            raise ValueError("invalid agent id")
        return value

    @staticmethod
    def _topic(value: str) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > 128:
            raise ValueError("invalid topic")
        return value.strip()

    def _count(self) -> int:
        if not self.log_path.exists():
            return 0
        return sum(1 for _ in self.log_path.open("r", encoding="utf-8"))

    def _rotate_if_full(self) -> None:
        """Archive a full active segment so long-running workers can continue."""
        if self._count() < self.config.max_messages:
            return
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return
        stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
        archive = self.archive_root / f"messages-{stamp}-{time.time_ns()}.jsonl"
        self.log_path.replace(archive)
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({
                "action": "rotate",
                "archive": str(archive),
                "reason": "active message quota reached",
                "timestamp": time.time(),
            }, sort_keys=True) + "\n")

    def publish(
        self,
        sender: str,
        recipient: str,
        topic: str,
        body: str,
        *,
        reply_to: str | None = None,
        ttl_seconds: int | None = None,
    ) -> AgentMessage:
        sender = self._agent(sender)
        recipient = self._agent(recipient)
        topic = self._topic(topic)
        if not isinstance(body, str) or not body.strip():
            raise ValueError("message body must be non-empty text")
        encoded = body.encode("utf-8")
        if len(encoded) > self.config.max_message_bytes:
            raise ValueError("message exceeds communication size limit")
        if ttl_seconds is not None and (ttl_seconds < 1 or ttl_seconds > 7 * 86400):
            raise ValueError("invalid message TTL")

        # Rotate before writing, rather than treating historical messages as a
        # permanent failure condition for the worker.
        self._rotate_if_full()

        stamp = time.time()
        raw = f"{sender}|{recipient}|{topic}|{stamp}|{body}".encode("utf-8")
        message = AgentMessage(
            message_id=hashlib.sha256(raw).hexdigest()[:20],
            sender=sender,
            recipient=recipient,
            topic=topic,
            body=body,
            created_at=stamp,
            reply_to=reply_to,
            ttl_seconds=ttl_seconds,
        )
        with self.log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(asdict(message), sort_keys=True) + "\n")
        self._audit("publish", message)
        return message

    def broadcast(self, sender: str, recipients: list[str], topic: str, body: str, *, ttl_seconds: int | None = None) -> list[AgentMessage]:
        if len(recipients) > self.config.max_recipients:
            raise ValueError("recipient fan-out exceeds limit")
        unique = list(dict.fromkeys(recipients))
        return [self.publish(sender, recipient, topic, body, ttl_seconds=ttl_seconds) for recipient in unique]

    def inbox(self, recipient: str, *, topic: str | None = None, limit: int = 50) -> list[AgentMessage]:
        recipient = self._agent(recipient)
        if limit < 1 or limit > 500:
            raise ValueError("invalid inbox limit")
        messages: list[AgentMessage] = []
        if not self.log_path.exists():
            return messages
        now = time.time()
        for line in self.log_path.open("r", encoding="utf-8"):
            item = AgentMessage(**json.loads(line))
            if item.recipient != recipient:
                continue
            if topic is not None and item.topic != topic:
                continue
            if item.ttl_seconds is not None and now > item.created_at + item.ttl_seconds:
                continue
            messages.append(item)
        return messages[-limit:]

    def conversation(self, agent_a: str, agent_b: str, *, limit: int = 100) -> list[AgentMessage]:
        agent_a, agent_b = self._agent(agent_a), self._agent(agent_b)
        if not self.log_path.exists():
            return []
        items = []
        for line in self.log_path.open("r", encoding="utf-8"):
            item = AgentMessage(**json.loads(line))
            if {item.sender, item.recipient} == {agent_a, agent_b}:
                items.append(item)
        return items[-limit:]

    def _audit(self, action: str, message: AgentMessage) -> None:
        record = {
            "action": action,
            "message_id": message.message_id,
            "sender": message.sender,
            "recipient": message.recipient,
            "topic": message.topic,
            "timestamp": time.time(),
        }
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")


__all__ = ["AgentCommunicationBus", "AgentMessage", "CommunicationConfig"]
