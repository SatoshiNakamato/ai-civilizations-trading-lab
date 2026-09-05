"""Deterministic, auditable lineage records for civilization evolution."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable


@dataclass(frozen=True)
class LineageRecord:
    generation: int
    parent_id: str
    child_id: str
    mutation: str
    created_at: float
    record_hash: str


class LineageLedger:
    def __init__(self) -> None:
        self._records: list[LineageRecord] = []
        self._children: set[str] = set()

    def spawn(self, parent_id: str, child_id: str, *, generation: int, mutation: str, created_at: float) -> LineageRecord:
        if not parent_id.strip() or not child_id.strip():
            raise ValueError("parent_id and child_id are required")
        if parent_id == child_id:
            raise ValueError("parent and child must differ")
        if generation < 1:
            raise ValueError("generation must be positive")
        if not mutation.strip():
            raise ValueError("mutation is required")
        if created_at < 0:
            raise ValueError("created_at must be non-negative")
        if child_id in self._children:
            raise ValueError("child already has a recorded parent")
        payload = f"{generation}|{parent_id}|{child_id}|{mutation}|{created_at:.6f}"
        record_hash = sha256(payload.encode()).hexdigest()
        record = LineageRecord(generation, parent_id, child_id, mutation, created_at, record_hash)
        self._records.append(record)
        self._children.add(child_id)
        return record

    def records(self) -> tuple[LineageRecord, ...]:
        return tuple(self._records)

    def ancestors(self, child_id: str) -> tuple[str, ...]:
        parent_by_child = {r.child_id: r.parent_id for r in self._records}
        result: list[str] = []
        current = child_id
        seen: set[str] = set()
        while current in parent_by_child and current not in seen:
            seen.add(current)
            current = parent_by_child[current]
            result.append(current)
        return tuple(result)

    def snapshot(self) -> dict:
        return {"records": len(self._records), "lineage": [{"generation": r.generation, "parent_id": r.parent_id, "child_id": r.child_id, "mutation": r.mutation, "record_hash": r.record_hash} for r in self._records]}
