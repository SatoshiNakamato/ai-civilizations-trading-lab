from __future__ import annotations
from dataclasses import dataclass

@dataclass
class FindingQuality:
    finding_id: str
    uses: int = 0
    helpful: int = 0
    harmful: int = 0

class ResearchQuality:
    """Measures whether research improves downstream outcomes."""
    def __init__(self): self.findings: dict[str, FindingQuality] = {}
    def record(self, finding_id: str, outcome: str):
        f = self.findings.setdefault(finding_id, FindingQuality(finding_id)); f.uses += 1
        if outcome == "helpful": f.helpful += 1
        elif outcome == "harmful": f.harmful += 1
        return f
    def score(self, finding_id: str) -> float:
        f = self.findings.get(finding_id)
        return 0.0 if not f else (f.helpful - f.harmful) / f.uses
    def snapshot(self):
        return {k: {"uses": v.uses, "helpful": v.helpful, "harmful": v.harmful, "score": self.score(k)} for k,v in self.findings.items()}
