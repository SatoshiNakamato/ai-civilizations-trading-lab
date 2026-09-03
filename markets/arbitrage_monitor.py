from __future__ import annotations

import time
from .cross_exchange import CrossExchangeArbitrageLab, CrossExchangeOpportunity


class ArbitrageMonitor:
    def __init__(self, lab: CrossExchangeArbitrageLab | None = None):
        self.lab = lab or CrossExchangeArbitrageLab()
        self.history: list[CrossExchangeOpportunity] = []

    def scan_once(self, symbols: list[str] | None = None) -> list[CrossExchangeOpportunity]:
        results = self.lab.inspect(symbols)
        self.history.extend(results)
        return results

    def run(self, seconds: int = 30, interval: float = 5.0, symbols: list[str] | None = None):
        end = time.time() + seconds
        while time.time() < end:
            yield self.scan_once(symbols)
            time.sleep(interval)
