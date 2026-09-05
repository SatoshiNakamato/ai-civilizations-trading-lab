from __future__ import annotations

import os
from dataclasses import dataclass
from time import time

from .notification_governor import NotificationGovernor


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
    """SMTP gateway for high-value civilization alerts.

    Delivery is delegated to NotificationGovernor so SMTP provider failures,
    especially Gmail quota responses, cannot crash or repeatedly restart the
    civilization worker.
    """

    def __init__(self, recipient: str | None = None, governor: NotificationGovernor | None = None):
        self.recipient = recipient or os.getenv("CIVILIZATION_ALERT_EMAIL", "iNeed2p@wearehackerone.com")
        self.min_confidence = float(os.getenv("CIVILIZATION_ALERT_MIN_CONFIDENCE", "0.80"))
        self.min_edge = float(os.getenv("CIVILIZATION_ALERT_MIN_EDGE", "0.005"))
        self.cooldown_seconds = int(os.getenv("CIVILIZATION_ALERT_COOLDOWN", "1800"))
        self.last_sent: dict[str, float] = {}
        self.sent = 0
        self.suppressed = 0
        self.governor = governor or NotificationGovernor()

    def enabled(self) -> bool:
        # Governor owns the complete SMTP credential check. This method keeps
        # the historical gateway API while avoiding secret values in snapshots.
        return self.governor._credentials() is not None and self.governor.config.enabled and self.governor.config.email_enabled

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

    @staticmethod
    def _message(candidate: AlertCandidate) -> tuple[str, str]:
        subject = f"[{candidate.severity}] Civilization alert: {candidate.title}"
        details = []
        if candidate.token_address:
            details.append(f"Contract address: {candidate.token_address}")
        if candidate.chain:
            details.append(f"Chain: {candidate.chain}")
        if candidate.url:
            details.append(f"Link: {candidate.url}")
        if candidate.buy_venue and candidate.sell_venue:
            details.append(f"Route: buy {candidate.buy_venue} @ {candidate.buy_price:.8g}; sell {candidate.sell_venue} @ {candidate.sell_price:.8g}")
        body = (
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
        return subject, body

    def send(self, candidate: AlertCandidate) -> bool:
        if not self.should_alert(candidate):
            return False
        subject, body = self._message(candidate)
        result = self.governor.notify(severity=candidate.severity, subject=subject, body=body)
        if result.get("sent"):
            key = f"{candidate.category}:{candidate.title.strip().lower()}"
            self.last_sent[key] = time()
            self.sent += 1
            return True
        self.suppressed += 1
        return False

    def snapshot(self):
        return {
            "enabled": self.enabled(),
            "recipient": self.recipient,
            "sent": self.sent,
            "suppressed": self.suppressed,
            "min_confidence": self.min_confidence,
            "min_edge": self.min_edge,
            "governor": self.governor.snapshot(),
        }
