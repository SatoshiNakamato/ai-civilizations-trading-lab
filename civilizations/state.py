"""Bounded, atomic persistence for civilization runtime state."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Mapping


@dataclass(frozen=True)
class StateSnapshot:
    generation: int
    run_id: str
    payload: Mapping[str, Any]


class StateStore:
    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, snapshot: StateSnapshot) -> Path:
        if snapshot.generation < 1 or not snapshot.run_id:
            raise ValueError("invalid state snapshot")
        target = self.root / "state.json"
        data = {"generation": snapshot.generation, "run_id": snapshot.run_id, "payload": dict(snapshot.payload)}
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.root, delete=False) as tmp:
            json.dump(data, tmp, sort_keys=True, separators=(",", ":"))
            tmp.flush()
            os.fsync(tmp.fileno())
            temp = Path(tmp.name)
        os.replace(temp, target)
        return target

    def load(self) -> StateSnapshot | None:
        target = self.root / "state.json"
        if not target.exists():
            return None
        data = json.loads(target.read_text(encoding="utf-8"))
        return StateSnapshot(int(data["generation"]), str(data["run_id"]), dict(data["payload"]))
