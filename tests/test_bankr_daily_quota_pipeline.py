import json

from markets.end_to_end import TradingCivilizationV1


def test_live_pipeline_skips_after_shared_three_launch_quota(monkeypatch, tmp_path):
    monkeypatch.setenv("BANKR_LIVE_DEPLOY", "1")
    for i in range(1, 5):
        monkeypatch.setenv(f"BANKR_API_KEY_{i}", f"key-{i}")

    civ = TradingCivilizationV1(
        agents=["A001", "A002", "A003", "A004"],
        data_dir=str(tmp_path),
        bankr_live=True,
    )

    # Seed three successful launches in the shared audit ledger. The fourth
    # agent must be deferred by the pipeline rather than making a fourth API call.
    audit = tmp_path / "bankr_token_plans.jsonl"
    for i in range(3):
        audit.write_text(
            (audit.read_text() if audit.exists() else "")
            + json.dumps({"status": "deployed", "created_at": 1000 + i})
            + "\n"
        )

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
    captured = []

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"tokenAddress":"0xTOKEN","txHash":"0xTX"}'

    def fake_urlopen(request, timeout=0):
        captured.append(json.loads(request.data.decode()))
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("time.time", lambda: 1000.0)

    result = civ.cycle()

    assert result["execution_intents"]
    assert captured
    assert captured[0]["description"] == result["bankr_plans"][0]["thesis"]
