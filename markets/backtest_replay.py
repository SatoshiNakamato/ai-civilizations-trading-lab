from dataclasses import dataclass

@dataclass
class ReplayPoint:
    ts:float; bid:float; ask:float

class BacktestReplay:
    def __init__(self,points=()): self.points=list(points)
    def run(self,step): return [step(p) for p in self.points]
    def add(self,point): self.points.append(point)
