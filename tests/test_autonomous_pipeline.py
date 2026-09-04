from civilizations.agent_brain import AgentBrain
from civilizations.research_debate import CrossAgentDebate
from markets.agent_pipeline import AutonomousResearchPipeline
from markets.evidence_verifier import EvidenceVerifier
from markets.deployment_policy import DeploymentPolicy


def test_pipeline_advances_strong_independent_signal(tmp_path):
    p = AutonomousResearchPipeline(
        brain=AgentBrain(str(tmp_path/'h.jsonl')),
        audit_path=str(tmp_path/'p.jsonl'))
    r = p.evaluate('A001','ALPHA','independent thesis', evidence=.95,
                   sources=['s1','s2','s3'], peer_scores=[.9,.85,.8],
                   independent_count=2, freshness=1, risk=.1,
                   authenticated=True)
    assert r.deployment_allowed


def test_pipeline_rejects_weak_evidence(tmp_path):
    p = AutonomousResearchPipeline(audit_path=str(tmp_path/'p.jsonl'))
    r = p.evaluate('A001','ALPHA','weak thesis', evidence=.1,
                   sources=['s1'], peer_scores=[.2,.3], independent_count=0,
                   freshness=.1, risk=.1, authenticated=True)
    assert not r.deployment_allowed
