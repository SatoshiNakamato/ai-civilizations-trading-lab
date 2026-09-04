from __future__ import annotations
from dataclasses import dataclass, asdict
import json
from pathlib import Path

from civilizations.agent_brain import AgentBrain
from civilizations.research_debate import CrossAgentDebate
from markets.evidence_verifier import EvidenceVerifier
from markets.deployment_policy import DeploymentPolicy

@dataclass
class PipelineResult:
    agent: str
    ticker: str
    hypothesis_score: float
    evidence_score: float
    debate_verdict: str
    deployment_allowed: bool
    reason: str

class AutonomousResearchPipeline:
    """Runs research-to-deployment decisions without interactive prompts.

    The pipeline decides whether to hand an approved plan to the existing Bankr
    adapter. The adapter remains responsible for the actual authenticated API call.
    """
    def __init__(self, brain=None, debate=None, verifier=None, policy=None, audit_path="data/autonomous_pipeline.jsonl"):
        self.brain = brain or AgentBrain()
        self.debate = debate or CrossAgentDebate()
        self.verifier = verifier or EvidenceVerifier()
        self.policy = policy or DeploymentPolicy()
        self.audit_path = Path(audit_path)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    def evaluate(self, agent, ticker, thesis, *, evidence, sources, peer_scores,
                 independent_count=0, freshness=1.0, executionability=1.0,
                 risk=0.2, deployments_today=0, authenticated=False):
        report = self.verifier.verify(sources, independent_count=independent_count, freshness=freshness)
        h = self.brain.generate(agent, ticker, thesis, evidence=report.score,
                                executionability=executionability, risk=risk)
        debate = self.debate.evaluate(h, peer_scores)
        allowed = debate.verdict == "advance" and report.valid
        decision = self.policy.evaluate(h, deployments_today=deployments_today, authenticated=authenticated) if allowed else None
        result = PipelineResult(agent, ticker, h.score, report.score, debate.verdict,
                                bool(decision and decision.allowed),
                                decision.reason if decision else ("debate/evidence gate rejected"))
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(result), sort_keys=True) + "\n")
        return result
