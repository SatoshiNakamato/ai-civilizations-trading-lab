import json

from release.validation import validate_fills, validate_paper_ledger
from markets.paper_reliability import PaperFill


def _fill(trade_id="t1"):
    return PaperFill(trade_id, "opp-1", "A001", "buy", "ABC", 1, 10, 10.1)


def test_validate_fills_accepts_valid_records():
    report = validate_fills([_fill()])
    assert report.healthy
    assert report.paper_trades == 1


def test_validate_fills_rejects_duplicates():
    report = validate_fills([_fill(), _fill()])
    assert not report.healthy
    assert report.duplicate_trade_ids == 1


def test_validate_paper_ledger_detects_malformed_lines(tmp_path):
    path = tmp_path / "paper.jsonl"
    path.write_text(json.dumps(_fill().__dict__) + "\nnot-json\n", encoding="utf-8")
    report = validate_paper_ledger(str(path))
    assert not report.healthy
    assert report.malformed_records == 1


def test_validate_paper_ledger_empty_is_healthy(tmp_path):
    report = validate_paper_ledger(str(tmp_path / "missing.jsonl"))
    assert report.healthy
    assert report.paper_trades == 0
