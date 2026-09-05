from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from time import time


@dataclass
class AlertCandidate:
    title: str
    category: str
    summary: str
    confidence: float
    edge: float = 0.0
    risk: float = 1.0
    sources: tuple[str, ...] = ()
    agent: str = "system"
    token_address: str = ""
    chain: str = ""
    url: str = ""
    buy_venue: str = ""
    sell_venue: str = ""
    buy_price: float = 0.0
    sell_price: float = 0.0

    @property
    def severity(self) -> str:
        if self.confidence >= 0.90 and self.edge >= 0.01 and self.risk <= 0.50:
            return "CRITICAL"
        if self.confidence >= 0.80 and (self.edge >= 0.005 or self.category in {"risk", "breakthrough"}):
            return "HIGH"
        if self.confidence >= 0.65:
            return "WATCH"
        return "NORMAL"


class EmailAlertGateway:
    """SMTP gateway for live human intelligence alerts.

    This gateway is deliberately separate from market execution. Civilization
    agents do not receive exchange or trading credentials; they only discover
    public opportunities. This component delivers qualifying arbitrage/alpha
    findings to the configured human recipient.
    """

    def __init__(self, recipient: str | None = None):
        self.recipient = recipient or os.getenv("CIVILIZATION_ALERT_EMAIL", "iNeed2p@wearehackerone.com")
        self.smtp_host = os.getenv("CIVILIZATION_SMTP_HOST", "")
        self.smtp_port = int(os.getenv("CIVILIZATION_SMTP_PORT", "587"))
        self.smtp_user = os.getenv("CIVILIZATION_SMTP_USER", "")
        self.smtp_password = os.getenv("CIVILIZATION_SMTP_PASSWORD", "")
        self.from_address = os.getenv("CIVILIZATION_ALERT_FROM", self.smtp_user)
        self.min_confidence = float(os.getenv("CIVILIZATION_ALERT_MIN_CONFIDENCE", "0.80"))
        self.min_edge = float(os.getenv("CIVILIZATION_ALERT_MIN_EDGE", "0.005"))
        self.cooldown_seconds = int(os.getenv("CIVILIZATION_ALERT_COOLDOWN", "1800"))
        self.max_retries = max(1, int(os.getenv("CIVILIZATION_ALERT_RETRIES", "3")))
        self.last_sent: dict[str, float] = {}
        self.sent = 0
        self.failed = 0
        self.suppressed = 0
        self.last_error = ""

    def enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password and self.recipient)

    def should_alert(self, candidate: AlertCandidate) -> bool:
        if candidate.severity not in {"CRITICAL", "HIGH"}:
            return False
        if candidate.confidence < self.min_confidence:
            return False
        if candidate.category in {"arbitrage", "alpha-token"} and candidate.edge < self.min_edge:
            return False
        key = f"{candidate.category}:{candidate.title.strip().lower()}"
        if time() - self.last_sent.get(key, 0) < self.cooldown_seconds:
            self.suppressed += 1
            return False
        return True

    def _message(self, candidate: AlertCandidate) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = f"[{candidate.severity}] Civilization alert: {candidate.title}"
        msg["From"] = self.from_address
        msg["To"] = self.recipient
        details = []
        if candidate.token_address:
            details.append(f"Contract address: {candidate.token_address}")
        if candidate.chain:
            details.append(f"Chain: {candidate.chain}")
        if candidate.url:
            details.append(f"Link: {candidate.url}")
        if candidate.buy_venue and candidate.sell_venue:
            details.append(
                f"Route: buy {candidate.buy_venue} @ {candidate.buy_price:.8g}; "
                f"sell {candidate.sell_venue} @ {candidate.sell_price:.8g}"
            )
        msg.set_content(
            f"Category: {candidate.category}\n"
            f"Severity: {candidate.severity}\n"
            f"Confidence: {candidate.confidence:.1%}\n"
            f"Estimated edge: {candidate.edge:.2%}\n"
            f"Risk score: {candidate.risk:.2f}\n"
            f"Agent: {candidate.agent}\n"
            f"Sources: {', '.join(candidate.sources) or 'none'}\n"
            + ("\n".join(details) + "\n" if details else "")
            + f"\n{candidate.summary}\n"
        )
        return msg

    def send(self, candidate: AlertCandidate) -> bool:
        if not self.should_alert(candidate) or not self.enabled():
            return False

        key = f"{candidate.category}:{candidate.title.strip().lower()}"
        msg = self._message(candidate)
        self.last_error = ""
        for attempt in range(1, self.max_retries + 1):
            try:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20) as smtp:
                    smtp.starttls()
                    smtp.login(self.smtp_user, self.smtp_password)
                    smtp.send_message(msg)
                self.last_sent[key] = time()
                self.sent += 1
                return True
            except (OSError, smtplib.SMTPException) as exc:
                self.last_error = f"attempt {attempt}/{self.max_retries}: {type(exc).__name__}: {exc}"

        self.failed += 1
        return False

    def snapshot(self):
        return {
            "enabled": self.enabled(),
            "recipient": self.recipient,
            "sent": self.sent,
            "failed": self.failed,
            "suppressed": self.suppressed,
            "last_error": self.last_error,
            "min_confidence": self.min_confidence,
            "min_edge": self.min_edge,
            "retries": self.max_retries,
        }
