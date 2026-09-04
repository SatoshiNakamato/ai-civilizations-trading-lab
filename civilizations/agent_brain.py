from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib, json, time
from pathlib import Path

@dataclass
class ResearchHypothesis:
    agent: str
    hypothesis_id: str
    ticker: str
    thesis: str
    novelty: float
    evidence: float
    executionability: float
    risk: float
    score: float
    created_at: float

class AgentBrain:
    """Auditable research layer; upstream evidence must be supplied by feeds."""
    def __init__(self, audit_path="data/agent_hypotheses.jsonl"):
        self.audit_path = Path(audit_path); self.audit_path.parent.mkdir(parents=True, exist_ok=True)
    def generate(self, agent, ticker, thesis, *, evidence, executionability, risk, consensus_score=0.5):
        evidence=max(0,min(1,float(evidence))); executionability=max(0,min(1,float(executionability)))
        risk=max(0,min(1,float(risk))); consensus_score=max(0,min(1,float(consensus_score)))
        novelty=min(1,abs(consensus_score-.5)*2+.5)
        score=.35*evidence+.25*novelty+.25*executionability+.15*(1-risk)
        raw=f"{agent.upper()}|{ticker.upper()}|{thesis}|{time.time_ns()}".encode()
        result=ResearchHypothesis(agent.upper(),hashlib.sha256(raw).hexdigest()[:16],ticker.upper(),thesis[:1000],novelty,evidence,executionability,risk,score,time.time())
        with self.audit_path.open('a',encoding='utf-8') as f: f.write(json.dumps(asdict(result),sort_keys=True)+'\n')
        return result
