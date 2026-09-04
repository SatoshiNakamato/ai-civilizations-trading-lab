from __future__ import annotations

from dataclasses import dataclass, asdict
import os
import time

from markets.audit_log import AuditLog
from markets.continuous_arbitrage import ContinuousArbitrage
from markets.portfolio import Portfolio
from markets.strategy_metrics import StrategyMetrics
from risk.governor import RiskGovernor
from civilizations.alert_gate import AlertGate
from civilizations.research_opportunity_pipeline import ResearchOpportunityPipeline


@dataclass
class LifecycleEvent:
    cycle: int
    stage: str
    agent: str
    status: str
    payload: dict
    created_at: float


class TradingCivilizationV1:
    """Glue layer connecting research, arbitrage, paper execution and accounting."""
    def __init__(self, runtime=None, agents=None, data_dir="data/civilization"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.runtime = runtime
        self.agents = agents or [f"ARB-{i:02d}" for i in range(1, 11)]
        self.arbitrage = ContinuousArbitrage(runtime=runtime, agents=self.agents) if runtime else None
        self.pipeline = ResearchOpportunityPipeline()
        self.audit = AuditLog(os.path.join(data_dir, "lifecycle.jsonl"))
        self.portfolio = Portfolio()
        self.metrics = StrategyMetrics()
        self.risk = RiskGovernor()
        self.alerts = AlertGate()
        self.cycle_count = 0

    def cycle(self):
        self.cycle_count += 1
        result = {"cycle": self.cycle_count, "arbitrage": None, "portfolio": self.portfolio.snapshot()}
        if self.arbitrage:
            result["arbitrage"] = asdict(self.arbitrage.cycle())
        result["portfolio"] = self.portfolio.snapshot()
        self._event("cycle", "SYSTEM", "completed", result)
        return result

    def _event(self, stage, agent, status, payload):
        event = LifecycleEvent(self.cycle_count, stage, agent, status, payload, time.time())
        self.audit.append("lifecycle", **asdict(event))
        return event

    def snapshot(self):
        risk = {"exposure": self.risk.exposure, "daily_pnl": self.risk.daily_pnl, "halted": self.risk.halted}
        return {"cycles": self.cycle_count, "agents": len(self.agents),
                "arbitrage": self.arbitrage.snapshot() if self.arbitrage else None,
                "portfolio": self.portfolio.snapshot(), "risk": risk}
