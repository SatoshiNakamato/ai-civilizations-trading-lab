from __future__ import annotations

from dataclasses import dataclass, asdict
import time


@dataclass
class StageTelemetry:
    stage: str
    status: str
    count: int = 0
    detail: str = ""


class CycleTelemetry:
    """Small deterministic telemetry layer for hosted civilization cycles."""
    STAGES = (
        "research", "hypotheses", "debate", "evidence", "ranking", "risk",
        "deployment_policy", "bankr", "on_chain_observation", "pnl", "learning",
    )

    def __init__(self, cycle: int, agents: int):
        self.cycle = cycle
        self.agents = agents
        self.started_at = time.time()
        self.stages: list[StageTelemetry] = []

    def stage(self, name: str, status: str = "ok", count: int = 0, detail: str = ""):
        self.stages.append(StageTelemetry(name, status, count, detail))

    def snapshot(self) -> dict:
        return {
            "cycle": self.cycle,
            "agents": self.agents,
            "elapsed": time.time() - self.started_at,
            "stages": [asdict(s) for s in self.stages],
        }

    def log(self):
        for s in self.stages:
            extra = f" count={s.count}" if s.count else ""
            detail = f" {s.detail}" if s.detail else ""
            print(f"STAGE cycle={self.cycle} stage={s.stage} status={s.status}{extra}{detail}", flush=True)
