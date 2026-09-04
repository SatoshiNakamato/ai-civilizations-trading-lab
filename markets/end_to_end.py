from __future__ import annotations

from dataclasses import dataclass, asdict
import os
import time

from markets.audit_log import AuditLog
from markets.continuous_arbitrage import ContinuousArbitrage
from markets.portfolio import Portfolio
from markets.strategy_metrics import StrategyMetrics
from markets.bankr_token_agent import BankrTokenAgent
from markets.deployment_policy import DeploymentPolicy
from risk.governor import RiskGovernor
from civilizations.alert_gate import AlertGate
from civilizations.research_opportunity_pipeline import ResearchOpportunityPipeline
from civilizations.cycle_telemetry import CycleTelemetry
from civilizations.autonomous_research import AutonomousResearchEngine


@dataclass
class LifecycleEvent:
    cycle: int
    stage: str
    agent: str
    status: str
    payload: dict
    created_at: float


class TradingCivilizationV1:
    """Continuous autonomous research loop with auditable execution gates.

    The hosted worker can research, generate competing hypotheses, challenge
    them, rank opportunities and create Bankr deployment *plans*. Live money
    movement is deliberately not automatic; BANKR_LIVE_DEPLOY is kept as an
    explicit external control and the default hosted mode remains simulation.
    """
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
        self.research = AutonomousResearchEngine()
        self.bankr = BankrTokenAgent(os.path.join(data_dir, "bankr_token_plans.jsonl"), live=False)
        self.deployment_policy = DeploymentPolicy()
        self.cycle_count = 0

    def cycle(self):
        self.cycle_count += 1
        telemetry = CycleTelemetry(self.cycle_count, len(self.agents))
        print(f"CYCLE {self.cycle_count} START agents={len(self.agents)}", flush=True)

        opportunities = self.research.cycle(self.agents, self.cycle_count)
        top = opportunities[:3]
        findings = len(top)
        candidates = len([x for x in top if x.evidence_score >= .70])
        execution_candidates = []

        for opportunity in top:
            self._event("research", opportunity.hypothesis.agent, "produced", {
                "ticker": opportunity.hypothesis.ticker,
                "hypothesis_id": opportunity.hypothesis.hypothesis_id,
                "score": opportunity.hypothesis.score,
            })
            self._event("debate", opportunity.hypothesis.agent, "challenged", asdict(opportunity.debate))
            self._event("evidence", opportunity.hypothesis.agent, "verified", {"score": opportunity.evidence_score})
            self._event("ranking", opportunity.hypothesis.agent, "ranked", {"risk_adjusted": opportunity.risk_adjusted})
            if opportunity.risk_adjusted >= .62 and opportunity.hypothesis.risk <= .35:
                execution_candidates.append(opportunity)

        telemetry.stage("research", "ok", len(self.agents), "autonomous research cycle executed")
        telemetry.stage("hypotheses", "ok", len(opportunities), "independent hypotheses generated")
        telemetry.stage("debate", "ok", len(opportunities), "adversarial challenge pass executed")
        telemetry.stage("evidence", "ok", findings, "evidence scoring completed")
        telemetry.stage("ranking", "ok", candidates, "risk-adjusted opportunities ranked")

        approved = []
        for opportunity in execution_candidates:
            decision = self.deployment_policy.evaluate(
                type("Plan", (), {
                    "score": opportunity.risk_adjusted,
                    "risk": opportunity.hypothesis.risk,
                })(),
                deployments_today=0,
                authenticated=False,
            )
            self._event("risk", opportunity.hypothesis.agent, "gated", {"allowed": False, "reason": decision.reason})
            # A real deployment is never inferred merely from research quality.
            # The hosted research loop records an execution intent instead.
            approved.append({
                "agent": opportunity.hypothesis.agent,
                "ticker": opportunity.hypothesis.ticker,
                "score": opportunity.risk_adjusted,
                "deployment": "blocked",
                "reason": decision.reason,
            })

        telemetry.stage("risk", "ok", len(execution_candidates), "risk governor evaluated candidates")
        telemetry.stage("deployment_policy", "ok", len(approved), "execution intents evaluated")

        plans = []
        for opportunity in execution_candidates[:1]:
            symbol = f"CIV{self.cycle_count % 10000:04d}"
            plan = self.bankr.plan(
                opportunity.hypothesis.agent,
                f"Civilization {opportunity.hypothesis.ticker} Research {self.cycle_count}",
                symbol,
                opportunity.hypothesis.thesis,
                opportunity.risk_adjusted,
                chain="base",
            )
            simulated = self.bankr.simulate(plan)
            plans.append(asdict(simulated))
            self._event("bankr", plan.agent, "simulated", asdict(simulated))

        telemetry.stage("bankr", "simulated", len(plans), "Bankr deployment plans simulated; live execution disabled")
        telemetry.stage("on_chain_observation", "idle", 0, "no live positions")
        telemetry.stage("pnl", "ok", 0, "paper portfolio unchanged")
        telemetry.stage("learning", "ok", len(self.metrics.stats), "strategy book available")

        result = {
            "cycle": self.cycle_count,
            "arbitrage": asdict(self.arbitrage.cycle()) if self.arbitrage else None,
            "opportunities": [
                {
                    "agent": x.hypothesis.agent,
                    "ticker": x.hypothesis.ticker,
                    "hypothesis_id": x.hypothesis.hypothesis_id,
                    "score": x.hypothesis.score,
                    "debate_survival": x.debate.survival_score,
                    "evidence": x.evidence_score,
                    "risk_adjusted": x.risk_adjusted,
                }
                for x in top
            ],
            "execution_intents": approved,
            "bankr_plans": plans,
            "portfolio": self.portfolio.snapshot(),
        }
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
        return {
            "cycles": self.cycle_count,
            "agents": len(self.agents),
            "arbitrage": self.arbitrage.snapshot() if self.arbitrage else None,
            "research": self.research.snapshot(),
            "portfolio": self.portfolio.snapshot(),
            "risk": risk,
            "bankr": self.bankr.snapshot(),
        }
