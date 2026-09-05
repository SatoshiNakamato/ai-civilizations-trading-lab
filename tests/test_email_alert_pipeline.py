from civilizations.autonomous_research import DebateResult, Opportunity
from civilizations.agent_brain import ResearchHypothesis
from markets.end_to_end import TradingCivilizationV1


class FakeResearch:
    def __init__(self, opportunity):
        self.opportunity = opportunity
        self.last_signals = []

    def cycle(self, agents, cycle):
        return [self.opportunity]

    def snapshot(self):
        return {}


def make_opportunity():
    h = ResearchHypothesis(
        agent="A001", hypothesis_id="h-alpha", ticker="PEPE", thesis="fresh alpha token setup",
        novelty=0.9, evidence=0.98, executionability=0.98, risk=0.1, score=0.95, created_at=1.0,
    )
    d = DebateResult("h-alpha", 8, 2, ("liquidity may be insufficient",), 0.94)
    return Opportunity(h, d, 0.97, 0.95, 0.85)


def test_high_value_alpha_candidate_is_sent_to_existing_email_gateway(monkeypatch, tmp_path):
    sent = []
    monkeypatch.setattr("civilizations.email_alerts.EmailAlertGateway.send", lambda self, candidate: sent.append(candidate) or True)
    civ = TradingCivilizationV1(agents=["A001"], data_dir=str(tmp_path))
    civ.research = FakeResearch(make_opportunity())
    civ.bankr = type("FakeBankr", (), {
        "live": False, "recent_symbols": lambda self: set(), "snapshot": lambda self: {"live": False},
        "deployments_today": lambda self, agent: 0, "credential_configured": lambda self, agent: False,
        "plan": lambda *args: None,
        "simulate": lambda *args: type("R", (), {"status":"simulated","token_address":"","tx_hash":""})(),
    })()
    civ.arbitrage = type("FakeArb", (), {
        "cycle": lambda self: type("R", (), {"opened":0,"closed":0,"realized_pnl":0.0})(),
        "snapshot": lambda self: {},
    })()

    result = civ.cycle()

    assert sent
    assert sent[0].category == "alpha-token"
    assert sent[0].agent == "A001"
    assert result["alerts"]["alpha_sent"] == 1


def test_alert_gateway_recipient_comes_from_environment(monkeypatch):
    monkeypatch.setenv("CIVILIZATION_ALERT_EMAIL", "alerts@example.test")
    from civilizations.email_alerts import EmailAlertGateway
    gateway = EmailAlertGateway()
    assert gateway.recipient == "alerts@example.test"
