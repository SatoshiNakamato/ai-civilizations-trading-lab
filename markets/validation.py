from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class ValidationResult:
    candidate: str
    trials: int
    wins: int
    losses: int
    score: float


class ValidationLab:
    """Paper-trading/backtest scoreboard; never executes real orders."""

    def __init__(self):
        self.results: list[ValidationResult] = []

    def evaluate(self, candidate: str, returns: list[float]) -> ValidationResult:
        wins = sum(x > 0 for x in returns)
        losses = sum(x < 0 for x in returns)
        score = (sum(returns) / len(returns)) if returns else 0.0
        result = ValidationResult(candidate, len(returns), wins, losses, round(score, 8))
        self.results.append(result)
        return result

    def rank(self, limit: int = 10):
        return sorted(self.results, key=lambda x: (x.score, x.wins), reverse=True)[:limit]

    def snapshot(self):
        return {"trials": sum(r.trials for r in self.results), "candidates": len(self.results), "top": [asdict(r) for r in self.rank()]}
