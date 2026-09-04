from dataclasses import dataclass

@dataclass
class ResearchFinding:
    question:str; answer:str; sources:list; confidence:float=0.0

class ResearchOpportunityPipeline:
    def __init__(self,audit=None): self.audit=audit; self.findings=[]
    def ingest(self,finding):
        self.findings.append(finding)
        if self.audit: self.audit.append('research_finding',question=finding.question,confidence=finding.confidence,sources=finding.sources)
    def candidates(self): return [f for f in self.findings if f.confidence >= .8 and f.sources]
