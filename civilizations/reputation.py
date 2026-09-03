from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Reputation:
    agent_id: str
    verified: int = 0
    failed: int = 0
    collaborations: int = 0
    score: float = 0.0


class ReputationLedger:
    def __init__(self):
        self.agents: dict[str, Reputation] = {}

    def get(self, agent_id: str) -> Reputation:
        if agent_id not in self.agents:
            self.agents[agent_id] = Reputation(agent_id)
        return self.agents[agent_id]

    def record_verification(self, agent_id: str, passed: bool):
        r = self.get(agent_id)
        if passed:
            r.verified += 1
            r.score += 1.0
        else:
            r.failed += 1
            r.score -= 0.5
        return r

    def record_collaboration(self, agent_id: str):
        r = self.get(agent_id)
        r.collaborations += 1
        r.score += 0.1
        return r

    def rank(self):
        return sorted(self.agents.values(), key=lambda x: x.score, reverse=True)
