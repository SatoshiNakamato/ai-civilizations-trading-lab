from dataclasses import dataclass

from markets.end_to_end import TradingCivilizationV1


@dataclass
class Market:
    asset: str
    price_usd: float
    change_24h: float


class FakeAdapter:
    exchange_id = "fake"

    def ticker(self, symbol):
        return {"ask": 100.0, "last": 100.0}


class FakeEngine:
    def __init__(self):
        self.adapter = FakeAdapter()

    def snapshot(self):
        return {"fake": True}


class FakeLiveRuntime:
    def __init__(self):
        self.engine = FakeEngine()
        self.calls = []

    def execute(self, intent):
        self.calls.append(intent)
        return {"status": "submitted", "intent": intent.__dict__}

    def snapshot(self):
        return {"calls": len(self.calls)}


def test_live_pipeline_turns_positive_ranked_opportunity_into_trade_intent(monkeypatch, tmp_path):
    monkeypatch.setenv("LIVE_MAX_ORDER_QUOTE", "10")
    civ = TradingCivilizationV1(agents=["A001"], data_dir=str(tmp_path))
    civ.live_runtime = FakeLiveRuntime()

    opportunity = type("Opportunity", (), {})()
    hypothesis = type("Hypothesis", (), {
        "agent": "A001", "ticker": "BTC", "hypothesis_id": "h1",
        "score": 0.9, "thesis": "momentum", "risk": 0.1,
    })()
    opportunity.hypothesis = hypothesis
    opportunity.debate = type("Debate", (), {"survival_score": 0.9})()
    opportunity.evidence_score = 0.9
    opportunity.risk_adjusted = 0.9

    civ.research.cycle = lambda agents, cycle: [opportunity]
    civ.research.last_market = [Market("BTC", 100000.0, 4.0)]
    civ.bankr.recent_symbols = lambda: set()
    civ.bankr.plan = lambda *args, **kwargs: type("Plan", (), {"agent":"A001","name":"x","symbol":"X","thesis":"x"})()
    civ.deployment_policy.evaluate = lambda *args, **kwargs: type("Decision", (), {"allowed":False,"reason":"disabled"})()

    result = civ.cycle()
    assert result["live_results"][0]["status"] == "submitted"
    assert civ.live_runtime.calls[0].symbol == "BTC/USDT"
    assert civ.live_runtime.calls[0].side == "buy"
