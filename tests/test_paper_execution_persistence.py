import json

from markets.paper_execution import PaperExecutionEngine


def opportunity():
    class Opportunity:
        opportunity_id = "opp-1"
        asset = "BTC"
        buy_venue = "cheap"
        sell_venue = "rich"
        buy_price = 100.0
        sell_price = 103.0
        fees = 0.1
        slippage = 0.05
    return Opportunity()


def test_open_fill_survives_engine_restart(tmp_path):
    path = tmp_path / "fills.jsonl"
    first = PaperExecutionEngine(str(path))
    fill = first.open(opportunity(), agent="A001", quantity=2)

    second = PaperExecutionEngine(str(path))

    assert fill.fill_id in second.open_fills
    restored = second.open_fills[fill.fill_id]
    assert restored.agent == "A001"
    assert restored.quantity == 2
    assert second.snapshot()["open"] == 1


def test_closed_fill_is_restored_without_duplicate_entries(tmp_path):
    path = tmp_path / "fills.jsonl"
    first = PaperExecutionEngine(str(path))
    fill = first.open(opportunity(), agent="A001")
    first.close(fill.fill_id, 101.0, 102.5)

    second = PaperExecutionEngine(str(path))
    third = PaperExecutionEngine(str(path))

    assert fill.fill_id not in second.open_fills
    assert len(second.closed) == 1
    assert len(third.closed) == 1
    assert second.snapshot()["closed"] == 1
    assert second.snapshot()["realized_pnl"] > 0


def test_malformed_audit_records_do_not_break_restore(tmp_path):
    path = tmp_path / "fills.jsonl"
    path.write_text("not-json\n" + json.dumps({"event": "opened", "fill": {"bad": "record"}}) + "\n")

    engine = PaperExecutionEngine(str(path))

    assert engine.open_fills == {}
    assert engine.closed == []
