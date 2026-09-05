from __future__ import annotations
from dataclasses import dataclass
from civilizations.opportunities import OpportunityEngine
from civilizations.email_alerts import EmailAlertGateway
from markets.paper_execution import PaperExecutionEngine
from markets.trader_leaderboard import TraderLeaderboard
from markets.multi_exchange_arbitrage import MultiExchangeArbitrageScanner

@dataclass
class ArbitrageRuntime:
    scanner: object
    paper: PaperExecutionEngine
    leaderboard: TraderLeaderboard
    live_executor: object | None = None

    @classmethod
    def build(cls, audit_path="data/arbitrage_audit.jsonl", fills_path="data/paper_fills.jsonl"):
        engine=OpportunityEngine(audit_path)
        gateway=EmailAlertGateway()
        scanner=MultiExchangeArbitrageScanner(engine=engine, alert_gateway=gateway)
        return cls(scanner, PaperExecutionEngine(fills_path), TraderLeaderboard(), None)

    def scan_and_open(self, agent="ARB-TRADER"):
        # Public market intelligence only. Qualifying opportunities are emailed
        # for manual execution; this runtime never submits orders.
        return self.scanner.scan_once()

    def observe(self, quotes):
        return None

    def close(self, fill_id, quotes):
        return None

    def snapshot(self):
        return {
            "paper": {"enabled": False, "status": "disabled"},
            "leaderboard": self.leaderboard.snapshot(),
            "scanner": self.scanner.snapshot(),
            "live_arbitrage": {"enabled": False, "status": "alert-only"},
            "email_alerts": self.scanner.alert_gateway.snapshot() if getattr(self.scanner, "alert_gateway", None) else {"enabled": False},
        }
