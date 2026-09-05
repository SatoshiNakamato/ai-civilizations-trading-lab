import pytest

from civilizations.lineage import LineageLedger


def test_lineage_records_parent_child_and_ancestors():
    ledger = LineageLedger()
    ledger.spawn("CIV-A", "CIV-B", generation=1, mutation="risk-calibration", created_at=10)
    ledger.spawn("CIV-B", "CIV-C", generation=2, mutation="market-exploration", created_at=20)
    assert ledger.ancestors("CIV-C") == ("CIV-B", "CIV-A")
    assert ledger.records()[0].record_hash


def test_child_cannot_be_assigned_two_parents():
    ledger = LineageLedger()
    ledger.spawn("CIV-A", "CIV-B", generation=1, mutation="m1", created_at=10)
    with pytest.raises(ValueError, match="already has"):
        ledger.spawn("CIV-C", "CIV-B", generation=1, mutation="m2", created_at=11)


def test_lineage_rejects_self_parenting():
    with pytest.raises(ValueError, match="differ"):
        LineageLedger().spawn("CIV-A", "CIV-A", generation=1, mutation="m", created_at=10)
