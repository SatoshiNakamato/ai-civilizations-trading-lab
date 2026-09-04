from civilizations.bankr_token_agent import BankrTokenAgent


def test_plan_and_simulate(tmp_path):
    b = BankrTokenAgent(str(tmp_path / 'bankr.jsonl'), live=False)
    p = b.plan('A001', 'Alpha Civilization', 'alpha!', 'research-backed concept', .91, 'base')
    assert p.symbol == 'ALPHA'[:10]
    x = b.deploy(p)
    assert x.status == 'simulated'


def test_rejects_unsupported_chain(tmp_path):
    b = BankrTokenAgent(str(tmp_path / 'bankr.jsonl'), live=False)
    try:
        b.plan('A001', 'Alpha', 'ALPHA', 'x', .9, 'ethereum')
    except ValueError:
        return
    assert False


def test_100_agents_map_round_robin_to_four_wallet_keys(monkeypatch, tmp_path):
    for i in range(1, 5):
        monkeypatch.setenv(f'BANKR_API_KEY_{i}', f'test-{i}')
    b = BankrTokenAgent(str(tmp_path / 'bankr.jsonl'), live=True)
    assert b.credential_env('A001') == 'BANKR_API_KEY_1'
    assert b.credential_env('A002') == 'BANKR_API_KEY_2'
    assert b.credential_env('A003') == 'BANKR_API_KEY_3'
    assert b.credential_env('A004') == 'BANKR_API_KEY_4'
    assert b.credential_env('A005') == 'BANKR_API_KEY_1'
    assert b.credential_env('A100') == 'BANKR_API_KEY_4'
    assert len(b.configured_agents()) == 100
    assert all(b.configured_agents().values())


def test_creative_identity_is_valid_and_unique(tmp_path):
    b = BankrTokenAgent(str(tmp_path / 'bankr.jsonl'), live=False)
    used = set()
    name1, symbol1 = b.creative_identity('A001', 1, used)
    used.add(symbol1)
    name2, symbol2 = b.creative_identity('A005', 1, used)
    assert name1
    assert name2
    assert symbol1 != symbol2
    assert 1 <= len(symbol1) <= 10
    assert symbol1.isalnum()


def test_payload_only_contains_token_launch_fields(tmp_path):
    b = BankrTokenAgent(str(tmp_path / 'bankr.jsonl'), live=False)
    p = b.plan('A001', 'Alpha', 'ALPHA', 'thesis', .9, 'robinhood')
    payload = b.build_payload(p)
    assert payload['tokenName'] == 'Alpha'
    assert payload['tokenSymbol'] == 'ALPHA'
    assert payload['chain'] == 'robinhood'
    assert payload['simulateOnly'] is False
    assert not any(k in payload for k in ('recipientAddress', 'amount', 'transfer', 'swap', 'rawTransaction', 'privateKey'))


def test_auto_deploy_is_disabled_without_both_host_flags(monkeypatch, tmp_path):
    monkeypatch.delenv('BANKR_LIVE_DEPLOY', raising=False)
    monkeypatch.delenv('BANKR_AUTO_DEPLOY', raising=False)
    b = BankrTokenAgent(str(tmp_path / 'bankr.jsonl'))
    assert b.live is False
    assert b.auto_deploy is False


def test_unknown_agent_rejected(tmp_path):
    b = BankrTokenAgent(str(tmp_path / 'bankr.jsonl'), live=False)
    try:
        b.credential_env('A101')
    except ValueError:
        return
    assert False
