from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class TraderStats:
    agent: str
    pnl: float = 0.0
    trades: int = 0
    wins: int = 0
    losses: int = 0

class TraderLeaderboard:
    def __init__(self): self.stats=defaultdict(lambda: TraderStats(""))
    def record(self, agent, pnl):
        s=self.stats[agent]; s.agent=agent; s.pnl+=float(pnl); s.trades+=1
        if pnl>0: s.wins+=1
        elif pnl<0: s.losses+=1
    def top(self,n=3):
        return sorted((s for s in self.stats.values()),key=lambda s:(s.pnl,s.wins),reverse=True)[:n]
    def profitable(self,n=3): return [s for s in self.top(n) if s.pnl>0]
    def snapshot(self): return [{"agent":s.agent,"pnl":round(s.pnl,8),"trades":s.trades,"wins":s.wins,"losses":s.losses,"win_rate":s.wins/s.trades if s.trades else 0.0} for s in self.top(10)]
