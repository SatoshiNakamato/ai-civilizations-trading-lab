import json

from scripts.bankr_preflight import simulate
from markets.bankr_token_agent import BankrTokenAgent


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps({
            "success": True,
            "simulated": True,
            "tokenAddress": "0x1234567890abcdef1234567890abcdef12345678",
            "chain": "base",
        }).encode()


def test_preflight_always_uses_simulate_only(monkeypatch, tmp_path):
    monkeypatch.setenv("BANKR_API_KEY_1", "bk_usr_test_secret")
    requests = []

    def fake_urlopen(request, timeout=0):
        requests.append({
            "method": request.get_method(),
            "payload": json.loads(request.data.decode()),
            "headers": dict(request.headers),
        })
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    agent = BankrTokenAgent(str(tmp_path / "audit.jsonl"), live=True)
    result = simulate(agent, "A001", "base")

    assert result["ok"] is True
    assert result["simulated"] is True
    assert requests[0]["method"] == "POST"
    assert requests[0]["payload"]["simulateOnly"] is True
    assert requests[0]["headers"]["X-api-key"] == "bk_usr_test_secret"


def test_preflight_partner_key_requires_fee_recipient(monkeypatch, tmp_path):
    monkeypatch.setenv("BANKR_API_KEY_1", "bk_ptr_partner_secret")
    monkeypatch.delenv("BANKR_FEE_RECIPIENT", raising=False)
    agent = BankrTokenAgent(str(tmp_path / "audit.jsonl"), live=True)
    result = simulate(agent, "A001", "base")
    assert result["ok"] is False
    assert "BANKR_FEE_RECIPIENT" in result["error"]
