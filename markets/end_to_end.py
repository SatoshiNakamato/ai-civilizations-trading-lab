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
from civilizations.cycle_telemetry import CycleTelemetry


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
        self.pipeline = ResearchOpportunityPipeline(audit=None)
        self.audit = AuditLog(os.path.join(data_dir, "lifecycle.jsonl"))
        self.portfolio = Portfolio()
        self.metrics = StrategyMetrics()
        self.risk = RiskGovernor()
        self.alerts = AlertGate()
        self.cycle_count = 0

    def cycle(self):
        self.cycle_count += 1
        telemetry = CycleTelemetry(self.cycle_count, len(self.agents))
        print(f"CYCLE {self.cycle_count} START agents={len(self.agents)}", flush=True)

        # Telemetry is deliberately honest: a stage is only marked active when
        # the corresponding subsystem has produced work. This avoids claiming
        # that research/deployment occurred when the current runtime is paper-only.
        findings = len(self.pipeline.findings)
        candidates = len(self.pipeline.candidates())
        telemetry.stage("research", "ok", len(self.agents), "research subsystem ready")
        telemetry.stage("hypotheses", "ok", 0, "no hypotheses produced by current runtime")
        telemetry.stage("debate", "ok", 0, "no debate inputs")
        telemetry.stage("evidence", "ok", findings, "verified pipeline findings")
        telemetry.stage("ranking", "ok", candidates, "qualified research candidates")
        telemetry.stage("risk", "ok", 0, "no execution candidates")
        telemetry.stage("deployment_policy", "ok", 0, "execution not requested")

        result = {"cycle": self.cycle_count, "arbitrage": None, "portfolio": self.portfolio.snapshot()}
        if self.arbitrage:
            telemetry.stage("bankr", "ready", 0, "runtime adapter available; live deployment remains policy-gated")
            result["arbitrage"] = asdict(self.arbitrage.cycle())
        else:
            telemetry.stage("bankr", "idle", 0, "no trading runtime configured")

        telemetry.stage("on_chain_observation", "idle", 0, "no live positions")
        telemetry.stage("pnl", "ok", 0, "paper portfolio unchanged")
        telemetry.stage("learning", "ok", len(self.metrics.stats), "strategy book available")
        result["portfolio"] = self.portfolio.snapshot()
        result["telemetry"] = telemetry.snapshot()
        self._event("cycle", "SYSTEM", "completed", result)
        telemetry.log()
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
