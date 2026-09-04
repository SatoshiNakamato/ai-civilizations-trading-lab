import json
import urllib.error

from markets.bankr_token_agent import BankrTokenAgent


def test_partner_key_uses_partner_header():
    assert BankrTokenAgent._auth_headers("bk_ptr_abc") == {"X-Partner-Key": "bk_ptr_abc"}
    assert BankrTokenAgent._auth_headers("bk_usr_abc") == {"X-API-Key": "bk_usr_abc"}


def test_http_403_includes_bankr_message(tmp_path, monkeypatch):
    monkeypatch.setenv("BANKR_API_KEY_3", "bk_usr_test")
    monkeypatch.setenv("BANKR_LIVE_DEPLOY", "1")

    def fail(request, timeout=0):
        raise urllib.error.HTTPError(
            request.full_url,
            403,
            "Forbidden",
            {},
            __import__("io").BytesIO(json.dumps({
                "error": "Token Launch API access not enabled",
                "message": "Enable token launch access for this API key",
            }).encode()),
        )

    monkeypatch.setattr("urllib.request.urlopen", fail)
    monkeypatch.setattr("time.time", lambda: 1000.0)

    agent = BankrTokenAgent(str(tmp_path / "bankr.jsonl"), live=True)
    plan = agent.plan("A003", "Test Token", "TEST", "test", 0.9, "base")

    try:
        agent.deploy(plan)
    except RuntimeError as exc:
        text = str(exc)
        assert "HTTP 403" in text
        assert "Enable token launch access" in text
    else:
        raise AssertionError("expected Bankr 403")
