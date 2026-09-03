from __future__ import annotations

from dataclasses import dataclass, asdict
from time import time
from typing import Any

from .opportunity_lifecycle import DepthLevel, OpportunityMemory, assess_opportunity
from .opportunity_feedback import OpportunityFeedback


@dataclass(frozen=True)
class AgentScore:
    agent_id: str
    observations: int
    successes: int
    failures: int
    accuracy: float
    reputation: float


class CivilizationMarketHub:
    """Research-only coordination layer. Never signs, sends, or spends transactions."""

    def __init__(self):
        self.memory = OpportunityMemory()
        self.feedback = OpportunityFeedback()
        self.agent_results: dict[str, list[bool]] = {}
        self.events: list[dict[str, Any]] = []

    def assess(self, agent_id: str, symbol: str, buy_venue: str, sell_venue: str, buy_ask: float, sell_bid: float, size_usd: float, buy_fee_pct: float, sell_fee_pct: float, gas_usd: float = 0.0, latency_haircut_pct: float = 0.0, buy_depth: list[DepthLevel] | None = None, sell_depth: list[DepthLevel] | None = None):
        result = assess_opportunity(symbol, buy_ask, sell_bid, size_usd, buy_fee_pct, sell_fee_pct, gas_usd, latency_haircut_pct, buy_depth, sell_depth)
        result = type(result)(result.symbol, buy_venue, sell_venue, result.size_usd, result.gross_usd, result.fees_usd, result.gas_usd, result.slippage_usd, result.latency_haircut_usd, result.expected_net_usd, result.confidence, result.executable, result.reason, result.timestamp)
        self.memory.record(result, "candidate" if result.executable else "rejected")
        self.events.append({"type": "opportunity", "agent_id": agent_id, "data": asdict(result), "at": time()})
        return result

    def verify_agent_claim(self, agent_id: str, hypothesis: str, success: bool):
        outcome = "success" if success else "failure"
        feedback = self.feedback.observe(hypothesis, outcome)
        self.agent_results.setdefault(agent_id, []).append(success)
        self.events.append({"type": "verification", "agent_id": agent_id, "hypothesis": hypothesis, "success": success, "at": time()})
        return feedback

    def agent_scores(self) -> list[AgentScore]:
        rows = []
        for agent_id, results in self.agent_results.items():
            n = len(results)
            wins = sum(results)
            accuracy = wins / n if n else 0.0
            # Shrink small samples toward neutral reputation.
            reputation = (accuracy * n + 0.5 * 10) / (n + 10)
            rows.append(AgentScore(agent_id, n, wins, n - wins, accuracy, reputation))
        return sorted(rows, key=lambda x: (x.reputation, x.observations), reverse=True)

    def dashboard(self) -> dict[str, Any]:
        stats = self.memory.statistics()
        return {
            "timestamp": time(),
            "mode": "read-only research",
            "opportunity_memory": stats,
            "agent_scores": [asdict(x) for x in self.agent_scores()],
            "hypothesis_feedback": self.feedback.snapshot(),
            "events": len(self.events),
            "execution_enabled": False,
        }
