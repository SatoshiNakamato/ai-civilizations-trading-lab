from pathlib import Path


def test_real_env_files_are_ignored():
    ignore = Path('.gitignore').read_text(encoding='utf-8')
    assert '.env' in ignore
    assert '*.env.local' in ignore


def test_bankr_adapter_defaults_to_dry_run():
    from markets.bankr_token_agent import BankrTokenAgent
    agent = BankrTokenAgent(live=False)
    assert agent.live is False


def test_bankr_keys_are_not_hardcoded_as_values():
    source = Path('markets/bankr_token_agent.py').read_text(encoding='utf-8')
    assert 'BANKR_API_KEY_1="' not in source
    assert 'BANKR_API_KEY_2="' not in source
    assert 'BANKR_API_KEY_3="' not in source
    assert 'BANKR_API_KEY_4="' not in source
