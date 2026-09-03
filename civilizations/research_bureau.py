from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any


@dataclass
class ResearchFinding:
    agent_id: str
    question: str
    claim: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    peer_scores: list[float] = field(default_factory=list)

    @property
    def score(self) -> float:
        evidence_score = min(1.0, len(self.evidence) / 5.0)
        peer_score = mean(self.peer_scores) if self.peer_scores else 0.5
        return round(0.45 * self.confidence + 0.30 * evidence_score + 0.25 * peer_score, 6)


class ResearchBureau:
    """Coordinates read-only research among simulated citizens.

    Findings are hypotheses/evidence records, not trading instructions. The
    bureau never signs transactions, moves funds, or executes orders.
    """

    def __init__(self, web_research=None):
        self.web_research = web_research
        self.findings: list[ResearchFinding] = []
        self.questions: list[dict[str, Any]] = []
        self.generation = 0

    def submit_question(self, agent_id: str, question: str, priority: float = 0.5) -> None:
        self.questions.append({"agent_id": agent_id, "question": question, "priority": max(0.0, min(1.0, priority))})
        self.questions = sorted(self.questions, key=lambda x: x["priority"], reverse=True)[-200:]

    def investigate(self, agent_id: str, question: str, limit: int = 5) -> ResearchFinding:
        evidence = []
        if self.web_research is not None:
            try:
                evidence = self.web_research.search(question, limit=limit)
            except Exception as exc:
                evidence = [{"title": "research unavailable", "snippet": str(exc), "url": ""}]
        finding = ResearchFinding(
            agent_id=agent_id,
            question=question,
            claim="Evidence collected for agent review; claim requires validation.",
            evidence=evidence,
            confidence=0.25 if evidence else 0.05,
        )
        self.findings.append(finding)
        return finding

    def peer_review(self, finding: ResearchFinding, reviewer_scores: list[float]) -> float:
        finding.peer_scores.extend(max(0.0, min(1.0, x)) for x in reviewer_scores)
        return finding.score

    def best_findings(self, limit: int = 10) -> list[ResearchFinding]:
        return sorted(self.findings, key=lambda f: f.score, reverse=True)[:limit]

    def snapshot(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "questions": len(self.questions),
            "findings": len(self.findings),
            "top_findings": [
                {"agent_id": f.agent_id, "question": f.question, "score": f.score, "evidence": len(f.evidence)}
                for f in self.best_findings(10)
            ],
        }
