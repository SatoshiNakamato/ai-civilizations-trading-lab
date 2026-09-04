from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backtesting.validation import summarize_pnl, walk_forward_validate
from markets.audit_log import AuditLog
from markets.opportunity_attribution import Attribution, attribute
from markets.paper_reliability import PaperFill, PaperTradingLedger
from web.monitoring import monitoring_snapshot


@dataclass(frozen=True)
class FixtureReport:
    ledger: dict
    pnl: dict
    attribution: dict
    monitoring: dict
    backtest: dict


def _strategy(train, test):
    """Deterministic fixture strategy: replay the supplied OOS returns."""
    return [float(row["pnl"]) for row in test]


def build_paper_release_fixture(data_dir: str) -> FixtureReport:
    """Build a small, deterministic end-to-end paper-trading scenario.

    The fixture never calls an exchange, wallet, Bankr, or network endpoint.
    It exercises the release path from lifecycle audit through paper fills,
    attribution, P&L, walk-forward validation, and monitoring.
    """
    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)
    ledger = PaperTradingLedger(str(root / "paper_trades.jsonl"))
    audit = AuditLog(str(root / "audit.jsonl"))

    opportunities = [
        ("opp-alpha", "A001", "momentum", 12.0, 100.0, 0.80),
        ("opp-beta", "A002", "mean_reversion", -4.0, 80.0, 0.72),
        ("opp-gamma", "A003", "news", 9.0, 120.0, 0.91),
        ("opp-delta", "A004", "momentum", 3.0, 60.0, 0.67),
    ]
    fills: list[PaperFill] = []
    attributions: list[Attribution] = []
    for index, (opportunity_id, agent, category, pnl, notional, confidence) in enumerate(opportunities, start=1):
        symbol = f"FIX{index}"
        fill = PaperFill(
            trade_id=f"fixture-{index}",
            opportunity_id=opportunity_id,
            agent=agent,
            side="buy",
            symbol=symbol,
            quantity=1.0,
            requested_price=notional,
            fill_price=notional,
            timestamp=float(index),
        )
        ledger.record(fill)
        fills.append(fill)
        attributions.append(Attribution(opportunity_id, agent, category, pnl, notional, confidence))
        audit.append("paper_trade", opportunity_id=opportunity_id, agent=agent, symbol=symbol, pnl=pnl)

    pnl_values = [row[3] for row in opportunities]
    pnl = summarize_pnl(pnl_values)
    observations = [
        {"step": 1, "pnl": 5.0},
        {"step": 2, "pnl": -2.0},
        {"step": 3, "pnl": 7.0},
        {"step": 4, "pnl": 3.0},
        {"step": 5, "pnl": -1.0},
        {"step": 6, "pnl": 4.0},
    ]
    backtest = walk_forward_validate(observations, _strategy, train_size=3, test_size=1)

    return FixtureReport(
        ledger=ledger.validate(fills),
        pnl=pnl.__dict__,
        attribution=attribute(attributions),
        monitoring=monitoring_snapshot(data_dir),
        backtest=backtest,
    )
