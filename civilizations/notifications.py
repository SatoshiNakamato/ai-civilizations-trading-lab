"""Bounded, failure-isolated notifications for the AEON runtime."""
from __future__ import annotations

import hashlib
import os
import smtplib
import time
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Callable

SEVERITY = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int, minimum: int = 0) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


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
    max_per_day: int = 20
    cooldown_seconds: float = 0.0
    min_severity: str = "HIGH"
    enabled: bool = True
    email_enabled: bool = True
    digest_enabled: bool = False
    digest_interval_seconds: float = 3600.0

    @classmethod
    def from_env(cls) -> "NotificationGovernorConfig":
        severity = os.getenv("AEON_NOTIFICATION_MIN_SEVERITY", "HIGH").strip().upper()
        if severity not in SEVERITY:
            severity = "HIGH"
        return cls(
            max_notifications=_int("AEON_NOTIFICATION_MAX_PER_CYCLE", 3, 1),
            window_seconds=_float("AEON_NOTIFICATION_WINDOW_SECONDS", 300.0),
            dedupe_seconds=_float("AEON_NOTIFICATION_DEDUP_WINDOW_SECONDS", 86400.0),
            max_per_day=_int("AEON_NOTIFICATION_MAX_PER_DAY", 20, 1),
            cooldown_seconds=_float("AEON_NOTIFICATION_COOLDOWN_SECONDS", 900.0),
            min_severity=severity,
            enabled=_bool("AEON_NOTIFICATION_ENABLED", True),
            email_enabled=_bool("AEON_NOTIFICATION_EMAIL_ENABLED", True),
            digest_enabled=_bool("AEON_NOTIFICATION_DIGEST_ENABLED", False),
            digest_interval_seconds=_float("AEON_NOTIFICATION_DIGEST_INTERVAL_SECONDS", 3600.0),
        )


@dataclass(frozen=True)
class NotificationResult:
    sent: bool
    reason: str
    fingerprint: str


class SMTPEmailSender:
    """SMTP adapter using CIVILIZATION_* environment variables."""

    def __init__(self, *, host: str | None = None, port: int | None = None, user: str | None = None,
                 password: str | None = None, sender: str | None = None, recipient: str | None = None):
        self.host = host if host is not None else os.getenv("CIVILIZATION_SMTP_HOST", "").strip()
        self.port = port if port is not None else _int("CIVILIZATION_SMTP_PORT", 587, 1)
        self.user = user if user is not None else os.getenv("CIVILIZATION_SMTP_USER", "").strip()
        self.password = password if password is not None else os.getenv("CIVILIZATION_SMTP_PASSWORD", "")
        self.sender = sender if sender is not None else os.getenv("CIVILIZATION_ALERT_FROM", "").strip()
        self.recipient = recipient if recipient is not None else os.getenv("CIVILIZATION_ALERT_EMAIL", "").strip()

    def __call__(self, notification: Notification) -> None:
        if not self.host or not self.recipient:
            raise RuntimeError("notification SMTP configuration is incomplete")
        message = EmailMessage()
        message["Subject"] = notification.subject
        message["From"] = self.sender or self.user or self.recipient
        message["To"] = self.recipient
        message.set_content(notification.body)
        if self.port == 465:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=20) as smtp:
                if self.user:
                    smtp.login(self.user, self.password)
                smtp.send_message(message)
            return
        with smtplib.SMTP(self.host, self.port, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if self.user:
                smtp.login(self.user, self.password)
            smtp.send_message(message)


class NotificationGovernor:
    """Gate alerts so a 30-second worker cannot become an email storm."""

    def __init__(self, sender: Callable[[Notification], None], config: NotificationGovernorConfig | None = None,
                 *, clock: Callable[[], float] = time.time):
        self.sender = sender
        self.config = config or NotificationGovernorConfig.from_env()
        self.clock = clock
        if self.config.max_notifications < 1 or self.config.max_per_day < 1:
            raise ValueError("notification limits must be positive")
        self._sent_times: list[float] = []
        self._last_seen: dict[str, float] = {}
        self._day = self._today()
        self._day_count = 0
        self._last_sent = 0.0

    def _today(self) -> str:
        return time.strftime("%Y-%m-%d", time.localtime(self.clock()))

    def begin_cycle(self) -> None:
        self._sent_times.clear()
        today = self._today()
        if today != self._day:
            self._day = today
            self._day_count = 0
            self._last_seen.clear()
            self._last_sent = 0.0

    @staticmethod
    def fingerprint(severity: str, subject: str, body: str) -> str:
        payload = "|".join((severity.strip().lower(), subject.strip(), body.strip()))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]

    def notify(self, severity: str, subject: str, body: str) -> NotificationResult:
        severity = severity.strip().upper()
        if severity not in SEVERITY:
            raise ValueError("unsupported notification severity")
        fp = self.fingerprint(severity, subject, body)
        if not self.config.enabled or not self.config.email_enabled:
            return NotificationResult(False, "disabled", fp)
        if SEVERITY[severity] < SEVERITY[self.config.min_severity]:
            return NotificationResult(False, "below_min_severity", fp)
        now = self.clock()
        today = self._today()
        if today != self._day:
            self._day = today
            self._day_count = 0
            self._last_seen.clear()
            self._last_sent = 0.0
        self._sent_times = [t for t in self._sent_times if now - t < self.config.window_seconds]
        if len(self._sent_times) >= self.config.max_notifications:
            return NotificationResult(False, "rate_limited", fp)
        if self._day_count >= self.config.max_per_day:
            return NotificationResult(False, "rate_limited_day", fp)
        if self.config.cooldown_seconds and self._last_sent and now - self._last_sent < self.config.cooldown_seconds:
            return NotificationResult(False, "cooldown", fp)
        previous = self._last_seen.get(fp)
        if self.config.dedupe_seconds and previous is not None and now - previous < self.config.dedupe_seconds:
            return NotificationResult(False, "deduplicated", fp)
        notification = Notification(severity.lower(), subject, body, fp)
        try:
            self.sender(notification)
        except Exception as exc:
            # Provider failures, including Gmail 550/5.4.5 quota responses,
            # are isolated from the civilization worker.
            self._last_seen[fp] = now
            return NotificationResult(False, f"delivery_degraded:{type(exc).__name__}", fp)
        self._sent_times.append(now)
        self._last_seen[fp] = now
        self._last_sent = now
        self._day_count += 1
        return NotificationResult(True, "sent", fp)


__all__ = ["Notification", "NotificationGovernor", "NotificationGovernorConfig", "NotificationResult", "SMTPEmailSender"]
