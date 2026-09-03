from __future__ import annotations

from dataclasses import dataclass
from time import time

from .cognition import CognitiveEngine
from markets.live_research import LiveResearchScout


@dataclass
class AwakeningCycle:
    cycle: int
    agents: int
    market_findings: int
    cognitive_observations: int
    started_at: float


class CivilizationAwakening:
    """Coordinates repeated observe -> reason -> record cycles.

    Research and market access remain read-only. No trading or wallet signing
    is performed by this coordinator.
    """

    def __init__(self, agent_ids: list[str], scout: LiveResearchScout | None = None, cognition: CognitiveEngine | None = None):
        self.agent_ids = agent_ids
        self.scout = scout or LiveResearchScout()
        self.cognition = cognition or CognitiveEngine()
        self.cycle = 0

    def awaken_once(self) -> AwakeningCycle:
        self.cycle += 1
        findings = self.scout.scan()
        for agent_id in self.agent_ids:
            for finding in findings[:3]:
                observation = f"{finding.symbol} {finding.interval}: trend={finding.trend:.5f}, volatility={finding.volatility:.5f}, validation={finding.validation_score:.5f}"
                self.cognition.observe(agent_id, observation, min(1.0, finding.observations / 200))
                self.cognition.reason(agent_id, {"trend": finding.trend, "volatility": finding.volatility})
        return AwakeningCycle(self.cycle, len(self.agent_ids), len(findings), self.cognition.snapshot()["observations"], time())

    def snapshot(self):
        return {"cycle": self.cycle, "agents": len(self.agent_ids), "cognition": self.cognition.snapshot(), "market": self.scout.snapshot()}
