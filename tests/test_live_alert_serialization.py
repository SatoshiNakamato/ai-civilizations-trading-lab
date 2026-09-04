from markets.end_to_end import TradingCivilizationV1
from civilizations.autonomous_research import DebateResult, Opportunity
from civilizations.agent_brain import ResearchHypothesis


class FakeResearch:
    last_signals = []
    def cycle(self, agents, cycle):
        h = ResearchHypothesis("A001", "h1", "PEPE", "alpha", .9, .98, .98, .1, .95, 1.0)
        return [Opportunity(h, DebateResult("h1", 1, 0, (), .94), .97, .95, .85)]
    def snapshot(self): return {}


def test_cycle_accepts_lightweight_arbitrage_result(monkeypatch, tmp_path):
    sent = []
    monkeypatch.setattr("civilizations.email_alerts.EmailAlertGateway.send", lambda self, candidate: sent.append(candidate) or True)
    civ = TradingCivilizationV1(agents=["A001"], data_dir=str(tmp_path))
    civ.research = FakeResearch()
    civ.bankr = type("FakeBankr", (), {
        "live": False, "recent_symbols": lambda self: set(), "snapshot": lambda self: {"live": False},
        "deployments_today": lambda self, agent: 0, "credential_configured": lambda self, agent: False,
        "plan": lambda *args: None,
        "simulate": lambda *args: type("R", (), {"status": "simulated", "token_address": "", "tx_hash": ""})(),
    })()
    civ.arbitrage = type("FakeArb", (), {
        "cycle": lambda self: type("R", (), {"opened": 0, "closed": 0, "realized_pnl": 0.0})(),
        "snapshot": lambda self: {},
    })()

    result = civ.cycle()
    assert result["alerts"]["alpha_sent"] == 1
    assert result["arbitrage"] == {"opened": 0, "closed": 0, "realized_pnl": 0.0}
