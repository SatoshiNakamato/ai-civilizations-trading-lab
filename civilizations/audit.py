"""Tamper-evident append-only audit chain."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class AuditEntry:
    sequence: int
    event_type: str
    payload: dict
    previous_hash: str
    entry_hash: str


class AuditLedger:
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def append(self, event_type: str, payload: dict) -> AuditEntry:
        if not event_type.strip():
            raise ValueError("event_type is required")
        sequence = len(self._entries)
        previous = self._entries[-1].entry_hash if self._entries else "0" * 64
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = sha256(f"{sequence}|{event_type}|{canonical}|{previous}".encode()).hexdigest()
        entry = AuditEntry(sequence, event_type, dict(payload), previous, digest)
        self._entries.append(entry)
        return entry

    def entries(self) -> tuple[AuditEntry, ...]:
        return tuple(self._entries)

    def verify(self) -> bool:
        previous = "0" * 64
        for expected, entry in enumerate(self._entries):
            if entry.sequence != expected or entry.previous_hash != previous:
                return False
            canonical = json.dumps(entry.payload, sort_keys=True, separators=(",", ":"))
            expected_hash = sha256(f"{entry.sequence}|{entry.event_type}|{canonical}|{entry.previous_hash}".encode()).hexdigest()
            if entry.entry_hash != expected_hash:
                return False
            previous = entry.entry_hash
        return True
