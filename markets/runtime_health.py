from __future__ import annotations

import time


class RuntimeHealth:
    """Small dependency-free health model for long-running research services."""

    def __init__(self, stale_after_seconds: float = 120.0):
        self.started_at = time.time()
        self.stale_after_seconds = float(stale_after_seconds)
        self.last_success_at = 0.0
        self.last_error = ""
        self.cycles = 0

    def success(self):
        self.cycles += 1
        self.last_success_at = time.time()
        self.last_error = ""

    def failure(self, error: Exception | str):
        self.cycles += 1
        self.last_error = str(error)

    def snapshot(self) -> dict:
        now = time.time()
        stale = bool(self.last_success_at) and now - self.last_success_at > self.stale_after_seconds
        return {
            "status": "degraded" if self.last_error or stale else "healthy",
            "uptime_seconds": round(now - self.started_at, 3),
            "cycles": self.cycles,
            "last_success_at": self.last_success_at,
            "stale": stale,
            "last_error": self.last_error,
        }
