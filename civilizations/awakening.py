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
    """Repeated real-world observation, reasoning and belief-learning cycles."""

    def __init__(self, agent_ids: list[str], scout: LiveResearchScout | None = None,
                 cognition: CognitiveEngine | None = None, observations_per_agent: int = 10):
        self.agent_ids = agent_ids
        self.scout = scout or LiveResearchScout()
        self.cognition = cognition or CognitiveEngine()
        self.observations_per_agent = max(1, observations_per_agent)
        self.cycle = 0

    def awaken_once(self) -> AwakeningCycle:
        self.cycle += 1
        findings = self.scout.scan()
        usable = findings[:self.observations_per_agent]
        for agent_id in self.agent_ids:
            for finding in usable:
                evidence = min(1.0, finding.observations / 200.0)
                observation = (
                    f"{finding.symbol} {finding.interval}: trend={finding.trend:.5f}, "
                    f"volatility={finding.volatility:.5f}, validation={finding.validation_score:.5f}, "
                    f"drawdown={finding.max_drawdown:.5f}"
                )
                self.cognition.observe(agent_id, observation, evidence)
                reasoning = self.cognition.reason(agent_id, {
                    "trend": finding.trend,
                    "volatility": finding.volatility,
                })
                statement = f"{finding.symbol} {finding.interval}: {reasoning['conclusion']}"
                self.cognition.form_belief(agent_id, statement, reasoning["confidence"])
        return AwakeningCycle(self.cycle, len(self.agent_ids), len(findings),
                              self.cognition.snapshot()["observations"], time())

    def snapshot(self):
        return {"cycle": self.cycle, "agents": len(self.agent_ids),
                "observations_per_agent": self.observations_per_agent,
                "cognition": self.cognition.snapshot(), "market": self.scout.snapshot()}
