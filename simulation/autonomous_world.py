from __future__ import annotations
from dataclasses import dataclass, asdict
import time

@dataclass(frozen=True)
class WorldCycle:
    cycle: int
    completed: bool
    result: dict
    created_at: float

class AutonomousWorld:
    """Continuous controller for the trading civilization.

    It repeatedly invokes the existing civilization lifecycle. Sleeping is
    injectable so tests remain deterministic. The controller never bypasses
    research, risk, deployment, observation, or accounting gates.
    """
    def __init__(self, civilization, interval_seconds=60.0, sleeper=time.sleep):
        self.civilization = civilization
        self.interval_seconds = max(0.0, float(interval_seconds))
        self.sleeper = sleeper
        self.cycles = 0
        self.running = False

    def cycle(self):
        self.cycles += 1
        result = self.civilization.cycle()
        return WorldCycle(self.cycles, True, result, time.time())

    def run(self, *, max_cycles=None):
        self.running = True
        completed = 0
        try:
            while self.running and (max_cycles is None or completed < max_cycles):
                self.cycle()
                completed += 1
                if self.running and (max_cycles is None or completed < max_cycles):
                    self.sleeper(self.interval_seconds)
        finally:
            self.running = False
        return completed

    def stop(self):
        self.running = False

    def snapshot(self):
        return {"cycles": self.cycles, "running": self.running,
                "interval_seconds": self.interval_seconds,
                "civilization": self.civilization.snapshot()}
