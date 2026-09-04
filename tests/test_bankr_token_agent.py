from civilizations.bankr_token_agent import BankrTokenAgent


def test_plan_and_simulate(tmp_path):
    b = BankrTokenAgent(str(tmp_path / 'bankr.jsonl'), live=False)
    p = b.plan('A01', 'Alpha Civilization', 'alpha!', 'research-backed concept', .91, 'base')
    assert p.symbol == 'ALPHA!'.replace('!', '')[:10]
    x = b.deploy(p)
    assert x.status == 'simulated'


def test_rejects_unsupported_chain(tmp_path):
    b = BankrTokenAgent(str(tmp_path / 'bankr.jsonl'), live=False)
    try:
        b.plan('A01', 'Alpha', 'ALPHA', 'x', .9, 'ethereum')
    except ValueError:
        return
    assert False


def test_agent_credential_mapping(monkeypatch, tmp_path):
    monkeypatch.setenv('BANKR_API_KEY_1', 'test-1')
    monkeypatch.setenv('BANKR_API_KEY_2', 'test-2')
    monkeypatch.setenv('BANKR_API_KEY_3', 'test-3')
    monkeypatch.setenv('BANKR_API_KEY_4', 'test-4')
    b = BankrTokenAgent(str(tmp_path / 'bankr.jsonl'), live=True)
    assert b.credential_env('A001') == 'BANKR_API_KEY_1'
    assert b.credential_env('A002') == 'BANKR_API_KEY_2'
    assert b.credential_env('A003') == 'BANKR_API_KEY_3'
    assert b.credential_env('A004') == 'BANKR_API_KEY_4'
    assert b.configured_agents() == {'A001': True, 'A002': True, 'A003': True, 'A004': True}


def test_unknown_agent_has_no_credential(tmp_path):
    b = BankrTokenAgent(str(tmp_path / 'bankr.jsonl'), live=False)
    try:
        b.credential_env('A005')
    except ValueError:
        return
    assert False
