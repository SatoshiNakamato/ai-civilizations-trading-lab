from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from .intelligence import ArbitrageOpportunity, MarketIntelligence
from .prediction import PredictionAssessment, PredictionMarket, assess_market


@dataclass
class Candidate:
    agent_id: str
    kind: str
    thesis: str
    score: float = 0.0
    evidence: int = 0
    reviews: int = 0
    failures: int = 0


class MarketResearchCouncil:
    """Lets simulated agents propose, review, and rank market hypotheses."""

    def __init__(self, market: MarketIntelligence | None = None):
        self.market = market or MarketIntelligence()
        self.candidates: list[Candidate] = []
        self.generation = 0

    def submit(self, agent_id: str, kind: str, thesis: str, evidence: int = 0, score: float = 0.0) -> Candidate:
        candidate = Candidate(agent_id, kind, thesis, max(0.0, min(1.0, score)), max(0, evidence))
        self.candidates.append(candidate)
        return candidate

    def admit_arbitrage(self, agent_id: str, opportunities: list[ArbitrageOpportunity], min_spread_pct: float = 0.25) -> int:
        count = 0
        for opportunity in opportunities:
            if opportunity.spread_pct < min_spread_pct:
                continue
            score = min(1.0, opportunity.spread_pct / 5.0)
            self.submit(agent_id, "arbitrage", f"{opportunity.symbol}: {opportunity.buy_venue} -> {opportunity.sell_venue}", 2, score)
            count += 1
        return count

    def admit_prediction(self, agent_id: str, market: PredictionMarket, model_probability: float) -> Candidate:
        assessment = assess_market(market, model_probability)
        score = min(1.0, abs(assessment.edge) * 2.0)
        return self.submit(agent_id, "prediction", market.question, 1, score)

    def review(self, reviewer_id: str, candidate_index: int, support: bool, evidence_quality: float = 0.5) -> Candidate:
        candidate = self.candidates[candidate_index]
        candidate.reviews += 1
        quality = max(0.0, min(1.0, evidence_quality))
        if support:
            candidate.score = min(1.0, candidate.score * 0.8 + quality * 0.2 + 0.05)
        else:
            candidate.failures += 1
            candidate.score = max(0.0, candidate.score * 0.75 - 0.05)
        return candidate

    def rank(self, limit: int = 10) -> list[Candidate]:
        return sorted(self.candidates, key=lambda c: (c.score, c.evidence, -c.failures), reverse=True)[:limit]

    def snapshot(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "candidates": len(self.candidates),
            "top": [asdict(c) for c in self.rank(10)],
        }
