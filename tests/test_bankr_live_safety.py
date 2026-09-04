import json

from markets.bankr_token_agent import BankrTokenAgent


def test_live_deploy_rejects_simulation_response(monkeypatch, tmp_path):
    monkeypatch.setenv("BANKR_API_KEY_1", "bk_usr_test_secret")
    agent = BankrTokenAgent(str(tmp_path / "audit.jsonl"), live=True)
    plan = agent.plan("A001", "Test", "TEST", "research", 0.9, "base", risk=0.1)

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"success":true,"simulated":true,"tokenAddress":"0x123"}'

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout=0: Response())
    monkeypatch.setattr("time.time", lambda: 1000.0)

    try:
        agent.deploy(plan)
    except RuntimeError as exc:
        assert "simulation/no-transaction" in str(exc)
    else:
        raise AssertionError("live deployment must never accept a simulated response")

    assert agent.deployments_today() == 1


def test_shared_attempt_quota_counts_failed_live_attempt(tmp_path):
    audit = tmp_path / "audit.jsonl"
    audit.write_text("".join(json.dumps({"status": "attempted", "created_at": 1000 + i}) + "\n" for i in range(3)))
    agent = BankrTokenAgent(str(audit), live=True)
    assert agent.deployments_today() == 3
