import json

from markets.bankr_token_agent import BankrTokenAgent
from markets.deployment_verifier import DeploymentVerifier


class FakeResponse:
    status = 200

    def __init__(self, body):
        self.body = body

    def read(self):
        return json.dumps(self.body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_live_no_transaction_is_partial_simulation(monkeypatch, tmp_path):
    monkeypatch.setenv("BANKR_API_KEY_1", "fake-live-key")
    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout=45: FakeResponse({
        "status": "partial",
        "tokenAddress": "0xSIMULATED",
        "message": "Simulation complete. Token would deploy at 0xSIMULATED",
    }))
    monkeypatch.setattr("time.time", lambda: 1000.0)
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    agent = BankrTokenAgent(str(tmp_path / "bankr.jsonl"), live=True)
    plan = agent.plan("A001", "Signal Cat", "sigcat", "research", .9, "base")
    result = agent.deploy(plan)

    assert result.status == "partial_simulation"
    assert result.token_address == "0xSIMULATED"
    assert result.tx_hash == ""
    assert agent.deployments_today() == 0


def test_verifier_requires_receipt_and_contract(monkeypatch):
    calls = []
    verifier = DeploymentVerifier({"base": "https://rpc.test"})

    def fake_rpc(url, method, params):
        calls.append((method, params))
        if method == "eth_getTransactionReceipt":
            return {"status": "0x1", "blockNumber": "0x2"}
        if method == "eth_getCode":
            return "0x60016000"
        raise AssertionError(method)

    monkeypatch.setattr(verifier, "_rpc", fake_rpc)
    result = verifier.verify("base", "0xTOKEN", "0xTX")

    assert result.status == "verified"
    assert result.block_number == "0x2"
    assert [x[0] for x in calls] == ["eth_getTransactionReceipt", "eth_getCode"]


def test_verifier_marks_missing_receipt_pending():
    verifier = DeploymentVerifier({"base": "https://rpc.test"})
    verifier._rpc = lambda url, method, params: None
    result = verifier.verify("base", "0xTOKEN", "0xTX")
    assert result.status == "pending"


def test_verifier_marks_missing_tx_as_partial_simulation():
    result = DeploymentVerifier({"base": "https://rpc.test"}).verify("base", "0xTOKEN", "")
    assert result.status == "partial_simulation"
