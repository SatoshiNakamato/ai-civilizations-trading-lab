from civilizations.autonomous_research import AutonomousResearchEngine
from civilizations.market_research_feed import MarketObservation
from markets.bankr_token_agent import BankrTokenAgent
from markets.deployment_policy import DeploymentPolicy


class FakeFeed:
    def fetch(self, timeout=8):
        return [MarketObservation("BTC", 100000, 3.2), MarketObservation("ETH", 4000, -1.0), MarketObservation("SOL", 200, 5.0)]


def test_executor_agents_receive_independent_hypotheses(tmp_path):
    engine = AutonomousResearchEngine(feed=FakeFeed())
    opportunities = engine.cycle([f"A{i:03d}" for i in range(1, 101)], 1, limit=8)
    assert len(opportunities) == 8
    assert {x.hypothesis.agent for x in opportunities} >= {"A001", "A002", "A003", "A004"}
    assert all(x.debate.challengers > 0 for x in opportunities)
    assert engine.snapshot()["market_observations"]


def test_deployment_gate_matches_risk_adjusted_flow():
    policy = DeploymentPolicy()
    class Plan:
        score = .63
        risk = .20
    assert policy.evaluate(Plan(), deployments_today=0, authenticated=True).allowed
    Plan.score = .61
    assert not policy.evaluate(Plan(), deployments_today=0, authenticated=True).allowed


def test_bankr_execution_identity_cannot_be_unknown_agent(tmp_path):
    bankr = BankrTokenAgent(str(tmp_path / "bankr.jsonl"), live=False)
    try:
        bankr.credential_env("A005")
    except ValueError:
        return
    raise AssertionError("unknown agent unexpectedly received a Bankr credential")
