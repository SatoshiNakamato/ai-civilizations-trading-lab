"""Cooperative scheduler for repeated civilization cycles."""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic, sleep
from typing import Callable


@dataclass(frozen=True)
class ScheduleConfig:
    interval_seconds: float = 60.0
    max_steps: int | None = None


class CivilizationScheduler:
    def __init__(self, step: Callable[[], object], config: ScheduleConfig | None = None) -> None:
        self.step = step
        self.config = config or ScheduleConfig()
        if self.config.interval_seconds < 0:
            raise ValueError("interval_seconds cannot be negative")
        if self.config.max_steps is not None and self.config.max_steps < 1:
            raise ValueError("max_steps must be positive")

    def run(self) -> int:
        count = 0
        next_run = monotonic()
        while self.config.max_steps is None or count < self.config.max_steps:
            now = monotonic()
            if now < next_run:
                sleep(next_run - now)
            self.step()
            count += 1
            next_run = monotonic() + self.config.interval_seconds
        return count
