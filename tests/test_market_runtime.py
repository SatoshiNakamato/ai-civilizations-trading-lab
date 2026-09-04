from civilizations.opportunities import Opportunity
from markets.paper_ledger import PaperLedger
from markets.runtime_health import RuntimeHealth


def good_opportunity():
    return Opportunity(
        opportunity_id="opp-1", category="arbitrage", asset="BTC", summary="spread",
        confidence=.95, risk=.2, gross_edge=.02, fees=.004, slippage=.001,
        liquidity=1.0, sources=["live://a"], agents=["A1"],
        buy_venue="cheap", sell_venue="rich", buy_price=100_000, sell_price=102_000,
        status="validated", score=.9,
    )


def test_paper_ledger_records_without_execution(tmp_path):
    ledger = PaperLedger(str(tmp_path / "paper.jsonl"))
    trade = ledger.record(good_opportunity(), .01)
    assert trade.net_pnl > 0
    assert ledger.snapshot()["mode"] == "paper-only"
    assert (tmp_path / "paper.jsonl").exists()


def test_paper_ledger_rejects_bad_quantity(tmp_path):
    ledger = PaperLedger(str(tmp_path / "paper.jsonl"))
    try:
        ledger.record(good_opportunity(), 0)
        assert False
    except ValueError:
        pass


def test_runtime_health_transitions():
    health = RuntimeHealth()
    assert health.snapshot()["status"] == "healthy"
    health.failure("feed timeout")
    assert health.snapshot()["status"] == "degraded"
    health.success()
    assert health.snapshot()["status"] == "healthy"
