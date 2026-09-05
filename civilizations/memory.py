"""Deterministic bounded memory for cross-generation learning."""
from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from typing import Iterable


@dataclass(frozen=True)
class MemoryItem:
    generation: int
    key: str
    value: str


class CivilizationMemory:
    def __init__(self, capacity: int = 256) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self._items: deque[MemoryItem] = deque(maxlen=capacity)

    def remember(self, item: MemoryItem) -> None:
        if item.generation < 1 or not item.key:
            raise ValueError("invalid memory item")
        self._items.append(item)

    def recent(self, limit: int | None = None) -> tuple[MemoryItem, ...]:
        items = tuple(self._items)
        return items if limit is None else items[-max(0, limit):]

    def keys(self) -> tuple[str, ...]:
        return tuple(item.key for item in self._items)
