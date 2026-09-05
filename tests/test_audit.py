from civilizations.audit import AuditLedger


def test_audit_chain_is_append_only_and_verifiable():
    ledger = AuditLedger()
    first = ledger.append("forecast", {"id": "f1", "market": "BTCUSDT"})
    second = ledger.append("resolution", {"id": "f1", "event": True})
    assert first.sequence == 0
    assert second.previous_hash == first.entry_hash
    assert ledger.verify()


def test_empty_audit_chain_is_valid():
    assert AuditLedger().verify()
