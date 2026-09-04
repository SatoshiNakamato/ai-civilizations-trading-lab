import json

from civilizations.bankr_token_agent import BankrTokenAgent


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps({
            "tokenAddress": "0xTESTTOKEN",
            "txHash": "0xTESTTX",
        }).encode()


def test_live_deploy_posts_token_launch_request(monkeypatch, tmp_path):
    monkeypatch.setenv("BANKR_API_KEY_1", "fake-live-key")
    monkeypatch.setenv("BANKR_LIVE_DEPLOY", "1")

    requests = []

    def fake_urlopen(request, timeout=0):
        requests.append({
            "url": request.full_url,
            "method": request.get_method(),
            "headers": dict(request.headers),
            "payload": json.loads(request.data.decode()),
            "timeout": timeout,
        })
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("time.time", lambda: 1000.0)

    agent = BankrTokenAgent(str(tmp_path / "bankr.jsonl"), live=True)
    plan = agent.plan("A001", "Signal Cat", "sigcat", "research-backed meme concept", 0.91, "base")
    result = agent.deploy(plan)

    assert result.status == "deployed"
    assert result.token_address == "0xTESTTOKEN"
    assert result.tx_hash == "0xTESTTX"
    assert len(requests) == 1
    request = requests[0]
    assert request["url"] == agent.ENDPOINT
    assert request["method"] == "POST"
    assert request["headers"]["X-api-key"] == "fake-live-key"
    assert request["payload"] == {
        "tokenName": "Signal Cat",
        "tokenSymbol": "SIGCAT",
        "description": "research-backed meme concept",
        "chain": "base",
        "quoteOnlyFees": True,
        "simulateOnly": False,
    }
    assert "transfer" not in request["payload"]
    assert "withdraw" not in request["payload"]


def test_global_one_minute_cooldown_is_enforced(monkeypatch, tmp_path):
    monkeypatch.setenv("BANKR_API_KEY_1", "fake-live-key")
    monkeypatch.setenv("BANKR_API_KEY_2", "fake-live-key-2")
    monkeypatch.setenv("BANKR_LIVE_DEPLOY", "1")

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout=0: FakeResponse())
    monkeypatch.setattr("time.time", lambda: 1000.0)
    sleeps = []
    monkeypatch.setattr("time.sleep", lambda seconds: sleeps.append(seconds))

    agent = BankrTokenAgent(str(tmp_path / "bankr.jsonl"), live=True)
    first = agent.plan("A001", "First", "FIRST", "first", 0.9, "base")
    second = agent.plan("A002", "Second", "SECOND", "second", 0.9, "robinhood")

    agent.deploy(first)
    agent.deploy(second)

    assert sleeps == [60.0]
