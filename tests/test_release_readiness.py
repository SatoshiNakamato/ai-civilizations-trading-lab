from markets.opportunity_attribution import Attribution, attribute
from markets.paper_reliability import PaperFill, PaperTradingLedger
from backtesting.validation import summarize_pnl, walk_forward_validate
from web.monitoring import monitoring_snapshot, render_dashboard


def test_paper_ledger_rejects_duplicate(tmp_path):
    ledger = PaperTradingLedger(str(tmp_path / "paper.jsonl"))
    fill = PaperFill("t1", "o1", "A001", "buy", "ABC", 2, 10, 10.1)
    ledger.record(fill)
    try:
        ledger.record(fill)
        assert False
    except ValueError as exc:
        assert "duplicate" in str(exc)
    assert ledger.validate()["valid"]


def test_backtest_walk_forward_is_oos():
    result = walk_forward_validate(list(range(8)), lambda train, test: [1.0] * len(test), 4, 2)
    assert result["validated"]
    assert result["windows"] == 2
    assert result["out_of_sample"].net_pnl == 4.0


def test_attribution_by_agent_and_opportunity():
    rows = [
        Attribution("o1", "A001", "arb", 2, 100, .9),
        Attribution("o2", "A002", "meme", -1, 50, .7),
    ]
    result = attribute(rows)
    assert result["by_agent"]["A001"]["net_pnl"] == 2
    assert result["by_opportunity"]["o2"]["win_rate"] == 0
    assert result["total_pnl"] == 1


def test_monitoring_snapshot_is_renderable(tmp_path):
    snapshot = monitoring_snapshot(str(tmp_path))
    assert snapshot["health"] == "ok"
    assert "AI Civilization Trading Lab" in render_dashboard(snapshot)


def test_pnl_summary_handles_empty_series():
    result = summarize_pnl([])
    assert result.trades == 0
    assert result.net_pnl == 0
    assert result.max_drawdown == 0
