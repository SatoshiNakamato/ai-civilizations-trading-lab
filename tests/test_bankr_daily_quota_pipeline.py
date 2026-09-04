import json
from types import SimpleNamespace

from markets.end_to_end import TradingCivilizationV1


def _eligible_opportunity(agent="A001"):
    hypothesis = SimpleNamespace(
        agent=agent,
        ticker="BTC",
        hypothesis_id="test-hypothesis",
        thesis="agent-authored deployment thesis",
        score=0.9,
        risk=0.2,
    )
    debate = SimpleNamespace(
        hypothesis_id="test-hypothesis",
        supporters=8,
        challengers=2,
        objections=("test objection",),
        survival_score=0.85,
    )
    return SimpleNamespace(
        hypothesis=hypothesis,
        debate=debate,
        evidence_score=0.9,
        rank_score=0.85,
        risk_adjusted=0.75,
    )


def test_live_pipeline_skips_after_shared_three_launch_quota(monkeypatch, tmp_path):
    monkeypatch.setenv("BANKR_LIVE_DEPLOY", "1")
    for i in range(1, 5):
        monkeypatch.setenv(f"BANKR_API_KEY_{i}", f"key-{i}")

    civ = TradingCivilizationV1(
        agents=["A001", "A002", "A003", "A004"],
        data_dir=str(tmp_path),
        bankr_live=True,
    )
    civ.research.cycle = lambda agents, cycle: [_eligible_opportunity("A001")]
    civ.research.last_signals = []

    # Seed three successful launches in the shared audit ledger. The next
    # eligible agent must be deferred by the pipeline rather than making a
    # fourth API call. This test intentionally isolates quota behavior from
    # the live public research feed.
    audit = tmp_path / "bankr_token_plans.jsonl"
    audit.write_text("".join(
        json.dumps({"status": "deployed", "created_at": 1000 + i}) + "\n"
        for i in range(3)
    ))

    monkeypatch.setattr("time.time", lambda: 1003.0)
    result = civ.cycle()

    assert result["bankr_plans"]
    assert result["bankr_plans"][0]["status"] == "deferred"
    assert result["launch_intents"][0]["allowed"] is False
    assert "quota" in result["launch_intents"][0]["reason"]
    assert result["execution_intents"] == []


def test_live_pipeline_uses_agent_research_for_deployment(monkeypatch, tmp_path):
    monkeypatch.setenv("BANKR_LIVE_DEPLOY", "1")
    monkeypatch.setenv("BANKR_API_KEY_1", "key-1")

    civ = TradingCivilizationV1(
        agents=["A001"],
        data_dir=str(tmp_path),
        bankr_live=True,
    )
    civ.research.cycle = lambda agents, cycle: [_eligible_opportunity("A001")]
    civ.research.last_signals = []
    captured = []

    class Response:
        status = 200
        def __init__(self, body): self.body = body
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return self.body

    def fake_urlopen(request, timeout=0):
        # The pipeline first performs a GET to discover existing launches, then
        # POSTs the agent-authored launch payload. Keep both operations isolated.
        if request.data is None:
            return Response(b'{"launches":[]}')
        captured.append(json.loads(request.data.decode()))
        return Response(b'{"tokenAddress":"0xTOKEN","txHash":"0xTX"}')

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("time.time", lambda: 1000.0)

    result = civ.cycle()

    assert result["execution_intents"]
    assert captured
    assert captured[0]["description"] == result["bankr_plans"][0]["thesis"]
