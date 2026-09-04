from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class EvidenceReport:
    valid: bool
    score: float
    reason: str

class EvidenceVerifier:
    """Checks research evidence quality without fabricating external evidence."""
    def verify(self, sources, *, independent_count=0, freshness=1.0):
        count = len(sources or [])
        freshness = max(0.0, min(1.0, float(freshness)))
        independent_count = max(0, int(independent_count))
        score = min(1.0, 0.35 * min(count / 3, 1.0) + 0.35 * min(independent_count / 2, 1.0) + 0.30 * freshness)
        return EvidenceReport(score >= 0.65, score, "sufficient evidence" if score >= 0.65 else "insufficient independent evidence")
