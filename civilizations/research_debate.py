from __future__ import annotations
from dataclasses import dataclass
from statistics import mean

@dataclass(frozen=True)
class DebateResult:
    hypothesis_id: str
    supporters: int
    challengers: int
    consensus: float
    verdict: str

class CrossAgentDebate:
    """Adversarial consensus layer. Inputs are supplied evidence scores, not facts."""
    def evaluate(self, hypothesis, peer_scores):
        scores = [max(0.0, min(1.0, float(x))) for x in peer_scores]
        supporters = sum(x >= 0.7 for x in scores)
        challengers = len(scores) - supporters
        consensus = mean(scores) if scores else 0.0
        verdict = "advance" if consensus >= 0.72 and challengers <= supporters else "reject"
        return DebateResult(hypothesis.hypothesis_id, supporters, challengers, consensus, verdict)
