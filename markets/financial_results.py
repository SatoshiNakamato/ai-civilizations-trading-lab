from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from math import sqrt
from pathlib import Path
import json


@dataclass(frozen=True)
class PerformanceObservation:
    trade_id: str
    opportunity_id: str
    agent: str
    category: str
    net_pnl: float
    notional: float


class FinancialResults:
    """Measure financial outcomes from the paper ledger without executing orders."""

    def __init__(self, path: str = "data/financial_results.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.observations: list[PerformanceObservation] = []

    def record(self, trade, agent: str = "unknown", category: str = "unknown") -> PerformanceObservation:
        observation = PerformanceObservation(
            trade_id=trade.trade_id,
            opportunity_id=trade.opportunity_id,
            agent=agent,
            category=category,
            net_pnl=float(trade.net_pnl),
            notional=float(trade.quantity * trade.buy_price),
        )
        self.observations.append(observation)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(observation), separators=(",", ":")) + "\n")
        return observation

    @staticmethod
    def _drawdown(pnls: list[float]) -> float:
        equity = 0.0
        peak = 0.0
        worst = 0.0
        for pnl in pnls:
            equity += pnl
            peak = max(peak, equity)
            worst = min(worst, equity - peak)
        return worst

    def report(self) -> dict:
        pnls = [x.net_pnl for x in self.observations]
        notionals = [x.notional for x in self.observations]
        total_pnl = sum(pnls)
        total_notional = sum(notionals)
        wins = sum(1 for pnl in pnls if pnl > 0)
        losses = sum(1 for pnl in pnls if pnl < 0)
        mean = total_pnl / len(pnls) if pnls else 0.0
        variance = (sum((p - mean) ** 2 for p in pnls) / (len(pnls) - 1)) if len(pnls) > 1 else 0.0
        sharpe_like = (mean / sqrt(variance)) * sqrt(len(pnls)) if variance > 0 else 0.0

        def attribution(key: str) -> dict:
            groups: dict[str, list[float]] = defaultdict(list)
            for item in self.observations:
                groups[getattr(item, key)].append(item.net_pnl)
            return {
                name: {"trades": len(values), "net_pnl": round(sum(values), 8),
                       "win_rate": round(sum(v > 0 for v in values) / len(values), 4)}
                for name, values in sorted(groups.items())
            }

        return {
            "trades": len(self.observations),
            "net_pnl": round(total_pnl, 8),
            "notional": round(total_notional, 8),
            "return_on_notional": round(total_pnl / total_notional, 8) if total_notional else 0.0,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / len(pnls), 4) if pnls else 0.0,
            "max_drawdown": round(self._drawdown(pnls), 8),
            "sharpe_like": round(sharpe_like, 6),
            "by_agent": attribution("agent"),
            "by_category": attribution("category"),
            "mode": "paper-only",
            "path": str(self.path),
        }

    def snapshot(self) -> dict:
        return self.report()
