from __future__ import annotations

from dataclasses import dataclass
from .research_pipeline import RealMarketResearch


@dataclass
class ResearchFinding:
    agent_id: str
    symbol: str
    hypothesis: str
    evidence_score: float
    validation_score: float
    observations: int


class AgentResearchLab:
    def __init__(self, research: RealMarketResearch | None = None):
        self.research = research or RealMarketResearch()
        self.findings: list[ResearchFinding] = []

    def investigate(self, agent_id: str, symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 200) -> ResearchFinding:
        result = self.research.investigate(symbol, interval, limit)
        features = result["features"]
        validation = result["validation"]
        evidence = min(1.0, result["observations"] / 200.0)
        score = float(validation["score"])
        hypothesis = "continuation" if features["trend"] > 0 else "reversal/watch"
        finding = ResearchFinding(agent_id, symbol, hypothesis, evidence, score, result["observations"])
        self.findings.append(finding)
        return finding
