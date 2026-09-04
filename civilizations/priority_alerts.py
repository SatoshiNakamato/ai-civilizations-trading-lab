from __future__ import annotations

from dataclasses import dataclass
from time import time

from .email_alerts import AlertCandidate, EmailAlertGateway


@dataclass(frozen=True)
class PriorityAlert:
    candidate: AlertCandidate
    reason: str
    created_at: float


class PriorityAlertRouter:
    """Routes only urgent, validated findings to the existing email gateway."""

    def __init__(self, gateway: EmailAlertGateway | None = None):
        self.gateway = gateway or EmailAlertGateway()
        self.alerts_sent = 0
        self.alerts_suppressed = 0

    def route(self, candidate: AlertCandidate, reason: str = "validated high-priority finding") -> bool:
        """Send immediately when the existing conservative gateway approves it."""
        sent = self.gateway.send(candidate)
        if sent:
            self.alerts_sent += 1
        else:
            self.alerts_suppressed += 1
        return sent

    def urgent_arbitrage(self, *, title: str, summary: str, confidence: float,
                         edge: float, risk: float, sources: tuple[str, ...] = (),
                         agent: str = "system") -> bool:
        candidate = AlertCandidate(
            title=title,
            category="arbitrage",
            summary=summary,
            confidence=confidence,
            edge=edge,
            risk=risk,
            sources=sources,
            agent=agent,
        )
        return self.route(candidate, "validated arbitrage opportunity")

    def snapshot(self) -> dict:
        return {
            "alerts_sent": self.alerts_sent,
            "alerts_suppressed": self.alerts_suppressed,
            "gateway": self.gateway.snapshot(),
        }
