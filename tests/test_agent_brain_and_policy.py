from civilizations.agent_brain import AgentBrain
from markets.deployment_policy import DeploymentPolicy


def test_brain_rewards_evidence_and_execution(tmp_path):
    brain = AgentBrain(str(tmp_path / "h.jsonl"))
    x = brain.generate("A001", "ALPHA", "test thesis", evidence=.95, executionability=.9, risk=.1)
    assert x.score > .8
    assert x.agent == "A001"


def test_policy_blocks_unsafe_deployment():
    policy = DeploymentPolicy()
    class Plan:
        score = .95
        risk = .5
    assert not policy.evaluate(Plan(), deployments_today=0, authenticated=True).allowed


def test_policy_requires_auth_and_quota():
    policy = DeploymentPolicy()
    class Plan:
        score = .95
        risk = .1
    assert not policy.evaluate(Plan(), authenticated=False).allowed
    assert not policy.evaluate(Plan(), deployments_today=3, authenticated=True).allowed
    assert policy.evaluate(Plan(), deployments_today=0, authenticated=True).allowed
