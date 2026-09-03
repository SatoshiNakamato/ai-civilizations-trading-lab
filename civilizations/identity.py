from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Citizenship:
    citizen_id: str
    civilization_id: str
    birth_generation: int
    status: str = "active"


def create_citizenship(agent_id: str, generation: int = 0, civilization_id: str = "CIV-001") -> Citizenship:
    return Citizenship(
        citizen_id=f"CIT-{civilization_id}-{agent_id}",
        civilization_id=civilization_id,
        birth_generation=generation,
    )
