from __future__ import annotations
from time import time

class ResearchObservability:
    """Compact operational metrics for the research civilization."""
    def __init__(self):
        self.started_at=time(); self.cycles=0; self.errors=0; self.metrics={}
    def cycle(self, **metrics):
        self.cycles += 1
        for k,v in metrics.items(): self.metrics[k]=v
        return self.snapshot()
    def error(self): self.errors += 1
    def snapshot(self):
        return {"uptime_seconds": round(time()-self.started_at,2), "cycles":self.cycles, "errors":self.errors, "metrics":dict(self.metrics)}
