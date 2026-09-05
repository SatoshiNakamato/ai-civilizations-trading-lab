from __future__ import annotations
from dataclasses import dataclass, asdict
import os
from civilizations.live_arbitrage import LiveArbitrageScanner, PublicQuoteFeed, Quote
from civilizations.opportunities import OpportunityEngine
from civilizations.email_alerts import EmailAlertGateway
from markets.paper_execution import PaperExecutionEngine
from markets.trader_leaderboard import TraderLeaderboard

@dataclass
class ArbitrageRuntime:
    scanner: LiveArbitrageScanner
    paper: PaperExecutionEngine
    leaderboard: TraderLeaderboard
    live_executor: object | None = None

    @classmethod
    def build(cls, audit_path="data/arbitrage_audit.jsonl", fills_path="data/paper_fills.jsonl"):
        engine=OpportunityEngine(audit_path)
        gateway=EmailAlertGateway()
        scanner=LiveArbitrageScanner(PublicQuoteFeed(), engine, alert_gateway=gateway)
        live_executor=None
        if os.getenv("LIVE_ARBITRAGE") == "1":
            from execution.live_arbitrage import LiveArbitrageExecutor
            live_executor=LiveArbitrageExecutor(audit_path="data/live_arbitrage.jsonl")
        return cls(scanner, PaperExecutionEngine(fills_path), TraderLeaderboard(), live_executor)

    def scan_and_open(self, agent="ARB-TRADER"):
        opportunity=self.scanner.scan_once()
        if opportunity is None or opportunity.status != "validated": return None
        if self.live_executor is not None:
            return self.live_executor.execute(opportunity)
        return self.paper.open(opportunity, agent=agent)

    def observe(self, quotes: list[Quote]):
        by_venue={q.venue:q for q in quotes}
        return self.paper.observe(by_venue)

    def close(self, fill_id, quotes: list[Quote]):
        by_venue={q.venue:q for q in quotes}
        fill=self.paper.open_fills[fill_id]
        buy=by_venue[fill.buy_venue]; sell=by_venue[fill.sell_venue]
        closed=self.paper.close(fill_id,buy.ask,sell.bid)
        self.leaderboard.record(closed.agent,closed.realized_pnl)
        return closed

    def snapshot(self):
        return {
            "paper":self.paper.snapshot(),
            "leaderboard":self.leaderboard.snapshot(),
            "scanner":self.scanner.snapshot(),
            "live_arbitrage":asdict(self.live_executor.config) if self.live_executor is not None else {"enabled":False},
            "email_alerts":self.scanner.alert_gateway.snapshot() if self.scanner.alert_gateway else {"enabled":False},
        }
