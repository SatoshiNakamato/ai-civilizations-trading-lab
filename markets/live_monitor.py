from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from civilizations.live_arbitrage import LiveArbitrageScanner
from civilizations.email_alerts import EmailAlertGateway
from .paper_ledger import PaperLedger


@dataclass
class MonitorStats:
    cycles: int = 0
    opportunities: int = 0
    alerts: int = 0
    errors: int = 0
    last_cycle_at: float = 0.0


class LiveMarketMonitor:
    """Supervise live market research without placing financial orders."""

    def __init__(self, scanner: LiveArbitrageScanner, ledger: PaperLedger | None = None,
                 alerts: EmailAlertGateway | None = None, quantity: float = 0.01):
        self.scanner = scanner
        self.ledger = ledger or PaperLedger()
        self.alerts = alerts
        self.quantity = quantity
        self.stats = MonitorStats()

    def cycle(self):
        self.stats.cycles += 1
        self.stats.last_cycle_at = time.time()
        try:
            opportunity = self.scanner.scan_once()
            if opportunity is None:
                return None
            self.stats.opportunities += 1
            trade = self.ledger.record(opportunity, self.quantity)
            # Scanner owns alert policy. This monitor records paper outcomes only.
            if self.alerts:
                self.stats.alerts = self.alerts.snapshot()["sent"]
            return {"opportunity": opportunity, "paper_trade": trade, "ledger": self.ledger.snapshot()}
        except Exception:
            self.stats.errors += 1
            raise

    def run(self, cycles: int = 1, sleep_seconds: float = 5.0, on_cycle: Callable | None = None):
        results = []
        for index in range(max(0, cycles)):
            result = self.cycle()
            results.append(result)
            if on_cycle:
                on_cycle(result, self.stats)
            if index + 1 < cycles and sleep_seconds > 0:
                time.sleep(sleep_seconds)
        return results

    def snapshot(self) -> dict:
        return {"stats": vars(self.stats).copy(), "ledger": self.ledger.snapshot()}
