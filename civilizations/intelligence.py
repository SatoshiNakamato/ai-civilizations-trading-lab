from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntelligenceProfile:
    """Simulation capability score. IQ is a fictional configuration, not a real IQ test."""

    iq: int = 500
    reasoning: float = 1.0
    creativity: float = 1.0
    skepticism: float = 1.0
    learning: float = 1.0


DEFAULT_PROFILE = IntelligenceProfile()
