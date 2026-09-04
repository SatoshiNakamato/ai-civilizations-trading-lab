import os

from markets.bankr_token_agent import BankrTokenAgent


def test_four_agent_credential_mapping(monkeypatch):
    for i in range(1, 5):
        monkeypatch.setenv(f"BANKR_API_KEY_{i}", f"test-{i}")
    agent = BankrTokenAgent()
    assert agent.configured_agents() == {
        "A001": True, "A002": True, "A003": True, "A004": True,
    }
    assert agent.credential_env("A001") == "BANKR_API_KEY_1"
    assert agent.credential_env("A004") == "BANKR_API_KEY_4"


def test_missing_credential_is_reported(monkeypatch):
    for i in range(1, 5):
        monkeypatch.delenv(f"BANKR_API_KEY_{i}", raising=False)
    result = BankrTokenAgent().verify_agent("A001")
    assert result.configured is False
    assert result.authenticated is False


def test_auth_result_does_not_expose_key(monkeypatch):
    monkeypatch.setenv("BANKR_API_KEY_1", "SUPER-SECRET-KEY")
    result = BankrTokenAgent().verify_agent("A001")
    assert "SUPER-SECRET-KEY" not in result.error
