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
