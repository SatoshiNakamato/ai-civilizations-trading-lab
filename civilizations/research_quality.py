from __future__ import annotations
from dataclasses import dataclass

@dataclass
class FindingQuality:
    finding_id: str
    uses: int = 0
    helpful: int = 0
    harmful: int = 0

class ResearchQuality:
    """Measures downstream usefulness and provides a conservative promotion gate."""
    def __init__(self): self.findings: dict[str, FindingQuality] = {}

    def record(self, finding_id: str, outcome: str):
        f = self.findings.setdefault(finding_id, FindingQuality(finding_id)); f.uses += 1
        if outcome == "helpful": f.helpful += 1
        elif outcome == "harmful": f.harmful += 1
        return f

    def score(self, finding_id: str) -> float:
        f = self.findings.get(finding_id)
        return 0.0 if not f else (f.helpful - f.harmful) / f.uses

    def assess(self, results, min_results: int = 1):
        valid = [r for r in results if getattr(r, 'url', '') and getattr(r, 'snippet', '')]
        promote = len(valid) >= max(1, min_results)
        return {'promote': promote, 'quality': round(min(1.0, len(valid) / 3), 3), 'evidence_count': len(valid), 'reasons': ['source_backed'] if promote else ['empty_or_unverified']}

    def snapshot(self):
        return {k: {"uses": v.uses, "helpful": v.helpful, "harmful": v.harmful, "score": self.score(k)} for k,v in self.findings.items()}
