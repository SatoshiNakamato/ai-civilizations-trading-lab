from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VerificationResult:
    hypothesis: str
    train_score: float
    validation_score: float
    test_score: float
    drawdown: float
    robust: bool
    reason: str


def verify(hypothesis: str, train_score: float, validation_score: float,
           test_score: float, drawdown: float, min_score: float = 0.0) -> VerificationResult:
    robust = (
        train_score > min_score
        and validation_score > min_score
        and test_score > min_score
        and drawdown < 0.50
    )
    reason = "survived all three periods" if robust else "failed robustness gate"
    return VerificationResult(hypothesis, train_score, validation_score, test_score, drawdown, robust, reason)
