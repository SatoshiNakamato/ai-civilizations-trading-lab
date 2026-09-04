from __future__ import annotations
from dataclasses import dataclass
import time

from markets.arbitrage_runtime import ArbitrageRuntime

@dataclass
class CycleResult:
    cycle: int
    opened: int
    closed: int
    realized_pnl: float
    profitable_traders: list

class ContinuousArbitrage:
    """Repeated paper evaluation of live arbitrage opportunities."""
    def __init__(self, runtime=None, agents=None, max_open_per_agent=1):
        self.runtime = runtime or ArbitrageRuntime.build()
        self.agents = agents or ["ARB-01", "ARB-02", "ARB-03"]
        self.max_open_per_agent = max_open_per_agent
        self.open_by_agent = {a: [] for a in self.agents}
        self.cycle_count = 0
        self.started_at = time.time()

    def cycle(self):
        self.cycle_count += 1
        opened = 0
        closed = 0

        # Give each strategy agent a chance to discover a distinct opportunity.
        for agent in self.agents:
            if len(self.open_by_agent[agent]) >= self.max_open_per_agent:
                continue
            fill = self.runtime.scan_and_open(agent)
            if fill is not None:
                self.open_by_agent[agent].append(fill.fill_id)
                opened += 1

        # Refresh public quotes and close paper positions when their current spread
        # has converged enough to be realized. The scanner feed is reused here.
        if self.open_by_agent:
            quotes = self.runtime.scanner.feed.snapshot()
            for agent, fill_ids in self.open_by_agent.items():
                for fill_id in list(fill_ids):
                    fill = self.runtime.paper.open_fills.get(fill_id)
                    if fill is None:
                        fill_ids.remove(fill_id)
                        continue
                    venues = {q.venue: q for q in quotes}
                    if fill.buy_venue not in venues or fill.sell_venue not in venues:
                        continue
                    buy, sell = venues[fill.buy_venue], venues[fill.sell_venue]
                    # Close when the current spread has materially converged.
                    current_spread = sell.bid - buy.ask
                    entry_spread = fill.entry_sell - fill.entry_buy
                    if current_spread <= entry_spread * 0.35:
                        self.runtime.close(fill_id, quotes)
                        fill_ids.remove(fill_id)
                        closed += 1

        snap = self.runtime.snapshot()
        return CycleResult(self.cycle_count, opened, closed, snap["paper"]["realized_pnl"], self.runtime.leaderboard.profitable(3))

    def run(self, cycles=1, interval_seconds=5):
        results=[]
        for i in range(cycles):
            results.append(self.cycle())
            if i + 1 < cycles:
                time.sleep(interval_seconds)
        return results

    def snapshot(self):
        return {"cycles": self.cycle_count, "uptime_seconds": time.time()-self.started_at, "open_by_agent": {k:list(v) for k,v in self.open_by_agent.items()}, "runtime": self.runtime.snapshot()}
