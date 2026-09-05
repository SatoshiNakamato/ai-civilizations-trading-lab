from __future__ import annotations

import gc
import os
import resource
import time
from dataclasses import dataclass, field


@dataclass
class EnduranceController:
    """Low-memory watchdog for long-running mobile/Voroa simulations."""

    soft_limit_mb: float = float(os.getenv("AEON_MEMORY_SOFT_MB", "320"))
    hard_limit_mb: float = float(os.getenv("AEON_MEMORY_HARD_MB", "450"))
    minimum_budget: int = int(os.getenv("AEON_MIN_ACTIVE_BUDGET", "2"))
    maximum_budget: int = int(os.getenv("AEON_MAX_ACTIVE_BUDGET", "8"))
    gc_every: int = int(os.getenv("AEON_GC_EVERY", "5"))
    peak_mb: float = 0.0
    last_mb: float = 0.0
    collections: int = 0
    pressure_events: int = 0
    last_check: float = field(default_factory=time.monotonic)

    def rss_mb(self) -> float:
        """Return current RSS when Linux/Android exposes it, else peak RSS.

        ``ru_maxrss`` is a peak value, not current memory. Using it as the
        live pressure signal caused false pressure readings after a transient
        spike. Voroa/Termux runs use /proc, so current VmRSS is preferred.
        """
        try:
            with open("/proc/self/status", "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("VmRSS:"):
                        return float(line.split()[1]) / 1024.0
        except (OSError, ValueError, IndexError):
            pass
        value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        if value >= 1024 * 1024 * 1024:
            return value / (1024.0 * 1024.0)
        return value / 1024.0

    def sample(self) -> float:
        self.last_mb = self.rss_mb()
        self.peak_mb = max(self.peak_mb, self.last_mb)
        return self.last_mb

    def check(self, tick: int, budget: int) -> dict:
        if tick % max(1, self.gc_every) == 0:
            self.collections += gc.collect()
        self.sample()
        level = "normal"
        new_budget = max(self.minimum_budget, min(self.maximum_budget, budget))
        if self.last_mb >= self.hard_limit_mb:
            level = "critical"
            self.pressure_events += 1
            self.collections += gc.collect()
            new_budget = self.minimum_budget
        elif self.last_mb >= self.soft_limit_mb:
            level = "elevated"
            self.pressure_events += 1
            self.collections += gc.collect()
            new_budget = max(self.minimum_budget, budget // 2)
        elif self.last_mb < self.soft_limit_mb * 0.65 and budget < self.maximum_budget:
            new_budget = min(self.maximum_budget, budget + 1)
        self.last_check = time.monotonic()
        return {"rss_mb": round(self.last_mb, 2), "peak_rss_mb": round(self.peak_mb, 2), "level": level, "active_budget": new_budget, "pressure_events": self.pressure_events, "gc_collected": self.collections}

    def snapshot(self, budget: int) -> dict:
        self.sample()
        return {"rss_mb": round(self.last_mb, 2), "peak_rss_mb": round(self.peak_mb, 2), "soft_limit_mb": self.soft_limit_mb, "hard_limit_mb": self.hard_limit_mb, "pressure_events": self.pressure_events, "active_budget": budget}
