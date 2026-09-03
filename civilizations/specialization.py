from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class Specialty:
    name: str
    score: float = 0.0
    trials: int = 0
    wins: int = 0


class SpecializationRegistry:
    """Tracks specialties from measured research outcomes, not assigned IQ."""
    def __init__(self):
        self.data: dict[str, dict[str, Specialty]] = {}

    def record(self, agent_id: str, specialty: str, score: float) -> Specialty:
        bucket = self.data.setdefault(agent_id, {})
        s = bucket.setdefault(specialty, Specialty(specialty))
        s.trials += 1
        s.wins += int(score > 0)
        s.score = (s.score * (s.trials - 1) + score) / s.trials
        return s

    def best(self, agent_id: str) -> Specialty | None:
        values = list(self.data.get(agent_id, {}).values())
        return max(values, key=lambda x: x.score, default=None)

    def snapshot(self):
        return {a: [asdict(x) for x in v.values()] for a, v in self.data.items()}
