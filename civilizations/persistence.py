from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StateStore:
    """Atomic JSON persistence for local simulation state."""
    def __init__(self, path: str = "data/civilization_state.json"):
        self.path = Path(path)

    def save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
        tmp.replace(self.path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))
