from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class WalkForwardResult:
    samples: int
    trades: int
    wins: int
    losses: int
    total_return: float
    max_drawdown: float
    score: float


def evaluate_directional(closes: list[float], threshold: float = 0.0) -> WalkForwardResult:
    """Evaluate a simple directional hypothesis on observed closes.

    Signal at t uses only information through t; outcome is t+1.
    This is a research evaluator, not an execution engine.
    """
    if len(closes) < 3:
        return WalkForwardResult(len(closes), 0, 0, 0, 0.0, 0.0, 0.0)
    equity = 1.0
    peak = equity
    drawdown = 0.0
    wins = losses = trades = 0
    for i in range(1, len(closes) - 1):
        prior = closes[i] / closes[i - 1] - 1
        direction = 1 if prior > threshold else (-1 if prior < -threshold else 0)
        if direction == 0:
            continue
        outcome = closes[i + 1] / closes[i] - 1
        pnl = direction * outcome
        equity *= 1 + pnl
        trades += 1
        wins += pnl > 0
        losses += pnl < 0
        peak = max(peak, equity)
        drawdown = max(drawdown, 1 - equity / peak)
    total = equity - 1
    score = total / (1 + drawdown)
    return WalkForwardResult(len(closes), trades, wins, losses, total, drawdown, score)
