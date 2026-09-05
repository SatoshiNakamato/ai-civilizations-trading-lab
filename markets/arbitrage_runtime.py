from __future__ import annotations

from dataclasses import dataclass

from civilizations.email_alerts import EmailAlertGateway
from civilizations.opportunities import Opportunity, OpportunityEngine
from markets.multi_exchange_arbitrage import MultiExchangeArbitrageScanner
from markets.paper_execution import PaperExecutionEngine
from markets.trader_leaderboard import TraderLeaderboard


@dataclass
class ArbitrageRuntime:
    scanner: object
    paper: PaperExecutionEngine
    leaderboard: TraderLeaderboard
    live_executor: object | None = None

    @classmethod
    def build(
        cls,
        audit_path="data/arbitrage_audit.jsonl",
        fills_path="data/paper_fills.jsonl",
    ):
        engine = OpportunityEngine(audit_path)
        gateway = EmailAlertGateway()
        scanner = MultiExchangeArbitrageScanner(engine=engine, alert_gateway=gateway)
        return cls(scanner, PaperExecutionEngine(fills_path), TraderLeaderboard(), None)

    def scan_and_open(self, agent="ARB-TRADER"):
        """Scan public markets and record a paper fill for the best opportunity.

        Alerts remain notification-only; the paper fill is bookkeeping used by
        the convergence observer and leaderboard. No live order is submitted.
        """
        opportunity = self.scanner.scan_once()
        if opportunity is None:
            return None
        if not isinstance(opportunity, Opportunity):
            return None
        return self.paper.open(opportunity, agent=agent)

    def observe(self, quotes):
        """Mark open paper fills against the latest venue quotes."""
        results = self.paper.observe(quotes)
        for fill in results:
            self.leaderboard.record(fill.agent, fill.realized_pnl)
        return results

    def close(self, fill_id, quotes):
        """Close a paper fill using venue quotes and record its PnL."""
        fill = self.paper.open_fills.get(fill_id)
        if fill is None:
            return None

        buy_quote = quotes[fill.buy_venue]
        sell_quote = quotes[fill.sell_venue]
        buy_price = float(getattr(buy_quote, "ask", buy_quote["ask"] if isinstance(buy_quote, dict) else buy_quote))
        sell_price = float(getattr(sell_quote, "bid", sell_quote["bid"] if isinstance(sell_quote, dict) else sell_quote))
        closed = self.paper.close(fill_id, buy_price, sell_price)
        self.leaderboard.record(closed.agent, closed.realized_pnl)
        return closed

    def snapshot(self):
        scanner_gateway = getattr(self.scanner, "alert_gateway", None)
        return {
            "paper": self.paper.snapshot(),
            "leaderboard": self.leaderboard.snapshot(),
            "scanner": self.scanner.snapshot(),
            "live_arbitrage": {"enabled": False, "status": "alert-only"},
            "email_alerts": scanner_gateway.snapshot() if scanner_gateway else {"enabled": False},
        }
