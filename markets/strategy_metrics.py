from dataclasses import dataclass

@dataclass
class StrategyStats:
    count:int=0; wins:int=0; pnl:float=0.0; peak:float=0.0; drawdown:float=0.0
    def record(self,value):
        self.count += 1
        self.wins += int(value > 0)
        self.pnl += value
        self.peak = max(self.peak, self.pnl)
        self.drawdown = max(self.drawdown, self.peak-self.pnl)
    @property
    def win_rate(self): return self.wins/self.count if self.count else 0.0
    @property
    def score(self): return self.pnl/(1+self.drawdown)*(0.5+self.win_rate) if self.count else 0.0

class StrategyBook:
    def __init__(self): self.stats={}
    def record(self,name,value): self.stats.setdefault(name,StrategyStats()).record(value)
    def top(self,n=3): return sorted(self.stats.items(),key=lambda x:x[1].score,reverse=True)[:n]

# Backwards-compatible public name used by the hosted civilization runtime.
# StrategyBook remains the implementation; StrategyMetrics is the stable facade name.
class StrategyMetrics(StrategyBook):
    pass

__all__ = ["StrategyStats", "StrategyBook", "StrategyMetrics"]
