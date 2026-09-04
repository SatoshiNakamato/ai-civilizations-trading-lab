from types import SimpleNamespace

from civilizations.research_budget import ResearchBudget
from markets.financial_results import FinancialResults
from markets.paper_ledger import PaperLedger


def test_budget_allocates_50_arbitrage_and_50_other(tmp_path):
    budget = ResearchBudget(str(tmp_path / "budget.json"), daily_limit=100, arbitrage_limit=50)
    assert budget.snapshot()["arbitrage"]["limit"] == 50
    assert budget.snapshot()["other"]["limit"] == 50
    assert all(budget.reserve("arb") for _ in range(50))
    assert not budget.reserve("arb")
    assert all(budget.reserve("macro") for _ in range(50))
    assert not budget.reserve("macro")
    assert budget.snapshot()["total_used"] == 100


def test_paper_ledger_records_financial_results(tmp_path):
    opportunity = SimpleNamespace(
        opportunity_id="opp-1", asset="BTC", buy_venue="cheap", sell_venue="rich",
        buy_price=100.0, sell_price=102.0, fees=0.01, slippage=0.001,
        category="arbitrage", agents=["A002"],
    )
    ledger = PaperLedger(str(tmp_path / "trades.jsonl"), str(tmp_path / "results.jsonl"))
    trade = ledger.record(opportunity, quantity=1.0)
    assert round(trade.net_pnl, 6) == 0.9
    report = ledger.snapshot()["financial_results"]
    assert report["trades"] == 1
    assert report["net_pnl"] == 0.9
    assert report["by_agent"]["A002"]["trades"] == 1
    assert report["by_category"]["arbitrage"]["win_rate"] == 1.0
