"""Bounded notification governance for AEON runtime alerts.

The governor prevents notification storms, deduplicates repeated alerts, and treats
provider rate-limit failures as a degraded notification state rather than a runtime
failure. It deliberately contains no SMTP implementation: delivery is injected so
production providers and deterministic tests share the same policy layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import monotonic
from typing import Callable


@dataclass(frozen=True)
class Notification:
    severity: str
    subject: str
    body: str
    fingerprint: str


@dataclass(frozen=True)
class NotificationGovernorConfig:
    max_notifications: int = 3
    window_seconds: float = 300.0
    dedupe_seconds: float = 3600.0


@dataclass(frozen=True)
class NotificationResult:
    sent: bool
    reason: str
    fingerprint: str


class NotificationGovernor:
    """Policy gate for critical notifications; safe to call from hot loops."""

    def __init__(
        self,
        sender: Callable[[Notification], None],
        config: NotificationGovernorConfig | None = None,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.sender = sender
        self.config = config or NotificationGovernorConfig()
        self.clock = clock
        if self.config.max_notifications < 1:
            raise ValueError("max_notifications must be positive")
        if self.config.window_seconds <= 0 or self.config.dedupe_seconds <= 0:
            raise ValueError("notification windows must be positive")
        self._sent_times: list[float] = []
        self._last_seen: dict[str, float] = {}

    @staticmethod
    def fingerprint(severity: str, subject: str, body: str) -> str:
        payload = "|".join((severity.strip().lower(), subject.strip(), body.strip()))
        return sha256(payload.encode("utf-8")).hexdigest()[:24]

    def notify(self, severity: str, subject: str, body: str) -> NotificationResult:
        severity = severity.strip().lower()
        if severity not in {"critical", "high", "info"}:
            raise ValueError("unsupported notification severity")
        fp = self.fingerprint(severity, subject, body)
        now = self.clock()
        self._sent_times = [t for t in self._sent_times if now - t < self.config.window_seconds]
        previous = self._last_seen.get(fp)
        if previous is not None and now - previous < self.config.dedupe_seconds:
            return NotificationResult(False, "deduplicated", fp)
        if len(self._sent_times) >= self.config.max_notifications:
            return NotificationResult(False, "rate_limited", fp)
        notification = Notification(severity, subject, body, fp)
        try:
            self.sender(notification)
        except Exception as exc:
            # Provider throttling (including SMTP 550/5.4.5) must not crash the
            # civilization worker. The caller can observe degraded delivery.
            self._last_seen[fp] = now
            return NotificationResult(False, f"delivery_degraded:{type(exc).__name__}", fp)
        self._sent_times.append(now)
        self._last_seen[fp] = now
        return NotificationResult(True, "sent", fp)
