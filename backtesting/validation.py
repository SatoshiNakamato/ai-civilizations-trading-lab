from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import mean
from typing import Callable, Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class BacktestResult:
    trades: int
    net_pnl: float
    win_rate: float
    max_drawdown: float
    sharpe_like: float
    train_size: int
    test_size: int


def summarize_pnl(pnls: Sequence[float], train_size: int = 0, test_size: int | None = None) -> BacktestResult:
    values = [float(x) for x in pnls]
    equity = peak = 0.0
    drawdown = 0.0
    for pnl in values:
        equity += pnl
        peak = max(peak, equity)
        drawdown = min(drawdown, equity - peak)
    avg = mean(values) if values else 0.0
    variance = sum((x - avg) ** 2 for x in values) / (len(values) - 1) if len(values) > 1 else 0.0
    sharpe = avg / sqrt(variance) * sqrt(len(values)) if variance else 0.0
    return BacktestResult(
        trades=len(values), net_pnl=round(sum(values), 8),
        win_rate=round(sum(x > 0 for x in values) / len(values), 4) if values else 0.0,
        max_drawdown=round(drawdown, 8), sharpe_like=round(sharpe, 6),
        train_size=train_size, test_size=len(values) if test_size is None else test_size,
    )


def walk_forward_validate(
    observations: Sequence[T],
    strategy: Callable[[Sequence[T], Sequence[T]], Sequence[float]],
    train_size: int,
    test_size: int,
) -> dict:
    """Run non-overlapping train/test windows and report aggregate OOS metrics."""
    if train_size <= 0 or test_size <= 0:
        raise ValueError("train_size and test_size must be positive")
    if len(observations) < train_size + test_size:
        raise ValueError("not enough observations for one train/test window")
    results: list[BacktestResult] = []
    start = 0
    while start + train_size + test_size <= len(observations):
        train = observations[start:start + train_size]
        test = observations[start + train_size:start + train_size + test_size]
        results.append(summarize_pnl(strategy(train, test), train_size, len(test)))
        start += test_size
    pnls = [r.net_pnl for r in results]
    return {
        "windows": len(results),
        "out_of_sample": summarize_pnl(pnls),
        "window_results": [r.__dict__ for r in results],
        "validated": bool(results) and all(r.trades == test_size for r in results),
    }
