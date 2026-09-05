from __future__ import annotations

import hashlib
import json
import os
import smtplib
import time
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from threading import Lock
from typing import Callable


DEFAULT_STATE_PATH = Path(os.getenv("AEON_NOTIFICATION_STATE_PATH", "world_state/notification_governor.json"))


@dataclass(frozen=True)
class NotificationConfig:
    enabled: bool = True
    email_enabled: bool = True
    cooldown_seconds: float = 300.0
    dedup_enabled: bool = True
    dedup_window_seconds: float = 3600.0
    digest_enabled: bool = False
    digest_interval_seconds: float = 900.0
    max_per_cycle: int = 1
    max_per_day: int = 20
    min_severity: str = "HIGH"

    @classmethod
    def from_env(cls) -> "NotificationConfig":
        def boolean(name: str, default: bool) -> bool:
            raw = os.getenv(name)
            if raw is None:
                return default
            return raw.strip().lower() in {"1", "true", "yes", "on"}

        def number(name: str, default: float) -> float:
            try:
                return max(0.0, float(os.getenv(name, str(default))))
            except ValueError:
                return default

        def integer(name: str, default: int) -> int:
            try:
                return max(0, int(os.getenv(name, str(default))))
            except ValueError:
                return default

        return cls(
            enabled=boolean("AEON_NOTIFICATION_ENABLED", True),
            email_enabled=boolean("AEON_NOTIFICATION_EMAIL_ENABLED", True),
            cooldown_seconds=number("AEON_NOTIFICATION_COOLDOWN_SECONDS", 300),
            dedup_enabled=boolean("AEON_NOTIFICATION_DEDUP_ENABLED", True),
            dedup_window_seconds=number("AEON_NOTIFICATION_DEDUP_WINDOW_SECONDS", 3600),
            digest_enabled=boolean("AEON_NOTIFICATION_DIGEST_ENABLED", False),
            digest_interval_seconds=number("AEON_NOTIFICATION_DIGEST_INTERVAL_SECONDS", 900),
            max_per_cycle=integer("AEON_NOTIFICATION_MAX_PER_CYCLE", 1),
            max_per_day=integer("AEON_NOTIFICATION_MAX_PER_DAY", 20),
            min_severity=os.getenv("AEON_NOTIFICATION_MIN_SEVERITY", "HIGH").strip().upper() or "HIGH",
        )


class NotificationGovernor:
    """Fail-closed notification boundary with durable quota/cooldown protection.

    SMTP failures never escape into the civilization cycle. Provider quota
    responses such as Gmail 550/5.4.5 are persisted as a circuit-open state
    until the next local calendar day, preventing process restarts from creating
    a hot retry loop.
    """

    _LEVELS = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

    def __init__(
        self,
        config: NotificationConfig | None = None,
        *,
        clock: Callable[[], float] = time.time,
        state_path: Path | None = None,
    ):
        self.config = config or NotificationConfig.from_env()
        self.clock = clock
        self.state_path = state_path or DEFAULT_STATE_PATH
        self._lock = Lock()
        self._cycle_sent = 0
        self._day = self._today()
        self._day_sent = 0
        self._last_sent_at = 0.0
        self._seen: dict[str, float] = {}
        self._circuit_until = 0.0
        self._last_error: str | None = None
        self._load_state()
        self._roll_day_if_needed()

    def _today(self) -> str:
        return time.strftime("%Y-%m-%d", time.localtime(self.clock()))

    def _load_state(self) -> None:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return
        if not isinstance(data, dict):
            return
        if data.get("day") == self._day:
            self._day_sent = max(0, int(data.get("day_sent", 0)))
            self._last_sent_at = max(0.0, float(data.get("last_sent_at", 0.0)))
            self._seen = {
                str(k): float(v)
                for k, v in dict(data.get("seen", {})).items()
                if isinstance(v, (int, float))
            }
        self._circuit_until = max(0.0, float(data.get("circuit_until", 0.0)))
        self._last_error = data.get("last_error") if isinstance(data.get("last_error"), str) else None

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "day": self._day,
            "day_sent": self._day_sent,
            "last_sent_at": self._last_sent_at,
            "seen": self._seen,
            "circuit_until": self._circuit_until,
            "last_error": self._last_error,
        }
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        tmp.replace(self.state_path)

    def _roll_day_if_needed(self) -> None:
        today = self._today()
        if today == self._day:
            return
        self._day = today
        self._day_sent = 0
        self._last_sent_at = 0.0
        self._seen.clear()
        self._circuit_until = 0.0
        self._last_error = None
        self._save_state()

    def begin_cycle(self) -> None:
        with self._lock:
            self._cycle_sent = 0
            self._roll_day_if_needed()

    @staticmethod
    def fingerprint(subject: str, body: str) -> str:
        return hashlib.sha256(f"{subject}\n{body}".encode("utf-8")).hexdigest()

    def _credentials(self) -> tuple[str, str, str, int] | None:
        host = os.getenv("CIVILIZATION_SMTP_HOST")
        user = os.getenv("CIVILIZATION_SMTP_USER")
        password = os.getenv("CIVILIZATION_SMTP_PASSWORD")
        recipient = os.getenv("CIVILIZATION_ALERT_EMAIL")
        sender = os.getenv("CIVILIZATION_ALERT_FROM") or user
        if not host or not user or not password or not recipient or not sender:
            return None
        try:
            port = int(os.getenv("CIVILIZATION_SMTP_PORT", "587"))
        except ValueError:
            return None
        return sender, recipient, host, port

    @staticmethod
    def _is_daily_quota_error(exc: smtplib.SMTPDataError) -> bool:
        detail = exc.smtp_error
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", errors="replace")
        text = str(detail).lower()
        return exc.smtp_code in {421, 450, 451, 452, 550, 552, 554} and (
            "5.4.5" in text
            or "daily user sending limit" in text
            or "sending limit" in text
            or "quota" in text
        )

    def _next_day_timestamp(self) -> float:
        now = self.clock()
        local = time.localtime(now)
        tomorrow = time.mktime((local.tm_year, local.tm_mon, local.tm_mday + 1, 0, 0, 0, 0, 0, -1))
        return max(now + 300.0, tomorrow + 1.0)

    def allowed(self, severity: str, *, fingerprint: str | None = None) -> tuple[bool, str]:
        severity = severity.strip().upper()
        if not self.config.enabled or not self.config.email_enabled:
            return False, "disabled"
        if self._LEVELS.get(severity, -1) < self._LEVELS.get(self.config.min_severity, 3):
            return False, "below_min_severity"
        now = self.clock()
        with self._lock:
            self._roll_day_if_needed()
            if now < self._circuit_until:
                return False, "smtp_circuit_open"
            if self._cycle_sent >= self.config.max_per_cycle:
                return False, "cycle_limit"
            if self._day_sent >= self.config.max_per_day:
                return False, "daily_limit"
            if self._last_sent_at and now - self._last_sent_at < self.config.cooldown_seconds:
                return False, "cooldown"
            if fingerprint and self.config.dedup_enabled:
                previous = self._seen.get(fingerprint)
                if previous is not None and now - previous < self.config.dedup_window_seconds:
                    return False, "duplicate"
        if self._credentials() is None:
            return False, "credentials_unavailable"
        return True, "allowed"

    def notify(self, *, severity: str, subject: str, body: str) -> dict:
        fingerprint = self.fingerprint(subject, body)
        allowed, reason = self.allowed(severity, fingerprint=fingerprint)
        if not allowed:
            return {"sent": False, "reason": reason, "severity": severity.upper()}

        credentials = self._credentials()
        if credentials is None:
            return {"sent": False, "reason": "credentials_unavailable", "severity": severity.upper()}
        sender, recipient, host, port = credentials
        message = EmailMessage()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        try:
            with smtplib.SMTP(host, port, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(os.getenv("CIVILIZATION_SMTP_USER"), os.getenv("CIVILIZATION_SMTP_PASSWORD"))
                smtp.send_message(message)
        except smtplib.SMTPDataError as exc:
            with self._lock:
                self._last_error = type(exc).__name__
                self._circuit_until = self._next_day_timestamp() if self._is_daily_quota_error(exc) else self.clock() + max(self.config.cooldown_seconds, 300.0)
                self._save_state()
            return {"sent": False, "reason": "smtp_quota" if self._is_daily_quota_error(exc) else "smtp_error", "error": type(exc).__name__, "severity": severity.upper()}
        except smtplib.SMTPException as exc:
            with self._lock:
                self._last_error = type(exc).__name__
                self._circuit_until = self.clock() + max(self.config.cooldown_seconds, 300.0)
                self._save_state()
            return {"sent": False, "reason": "smtp_error", "error": type(exc).__name__, "severity": severity.upper()}
        except OSError as exc:
            with self._lock:
                self._last_error = type(exc).__name__
                self._circuit_until = self.clock() + max(self.config.cooldown_seconds, 300.0)
                self._save_state()
            return {"sent": False, "reason": "smtp_transport_error", "error": type(exc).__name__, "severity": severity.upper()}

        with self._lock:
            self._cycle_sent += 1
            self._day_sent += 1
            self._last_sent_at = self.clock()
            self._seen[fingerprint] = self._last_sent_at
            self._last_error = None
            self._save_state()
        return {"sent": True, "reason": "sent", "severity": severity.upper()}

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "cycle_sent": self._cycle_sent,
                "day_sent": self._day_sent,
                "day": self._day,
                "circuit_open": self.clock() < self._circuit_until,
                "last_error": self._last_error,
            }


__all__ = ["NotificationConfig", "NotificationGovernor"]
