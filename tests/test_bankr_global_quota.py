import json

import pytest

from markets.bankr_token_agent import BankrTokenAgent


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps({"tokenAddress": "0xTEST", "txHash": "0xTX"}).encode()


def test_free_quota_is_shared_across_agent_keys(monkeypatch, tmp_path):
    for i in range(1, 5):
        monkeypatch.setenv(f"BANKR_API_KEY_{i}", f"fake-key-{i}")
    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout=0: FakeResponse())
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    monkeypatch.setattr("time.time", lambda: 1000.0)

    agent = BankrTokenAgent(str(tmp_path / "bankr.jsonl"), live=True)
    for number, owner in enumerate(("A001", "A002", "A003"), start=1):
        plan = agent.plan(owner, f"Token {number}", f"TOK{number}", "research", 0.9, "base")
        assert agent.deploy(plan).status == "deployed"

    fourth = agent.plan("A004", "Token 4", "TOK4", "research", 0.9, "base")
    with pytest.raises(RuntimeError, match="free-account launch quota reached"):
        agent.deploy(fourth)

    assert agent.deployments_today("A001") == 3
    assert agent.deployments_today("A004") == 3
