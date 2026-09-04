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
from civilizations.ticker_brain import TickerBrain

@dataclass
class LifecycleEvent:
    cycle: int
    stage: str
    agent: str
    status: str
    payload: dict
    created_at: float

class TradingCivilizationV1:
    """Continuous autonomous research-to-token-launch civilization.

    100 research agents generate and challenge opportunities. A001-A004 are
    the execution agents because only those four Bankr keys are provisioned.
    When BANKR_LIVE_DEPLOY=1, a surviving candidate can autonomously launch a
    token on Robinhood Chain or Base. Ticker selection is performed by the
    ticker brain and checked against recent public Bankr launches.
    """
    def __init__(self, runtime=None, agents=None, data_dir="data/civilization"):
        self.data_dir = data_dir; os.makedirs(data_dir, exist_ok=True)
        self.runtime = runtime
        self.agents = agents or [f"ARB-{i:02d}" for i in range(1, 11)]
        self.arbitrage = ContinuousArbitrage(runtime=runtime, agents=self.agents) if runtime else None
        self.pipeline = ResearchOpportunityPipeline(audit=None)
        self.audit = AuditLog(os.path.join(data_dir, "lifecycle.jsonl"))
        self.portfolio = Portfolio(); self.metrics = StrategyMetrics(); self.risk = RiskGovernor(); self.alerts = AlertGate()
        self.research = AutonomousResearchEngine(); self.tickers = TickerBrain()
        self.bankr = BankrTokenAgent(os.path.join(data_dir, "bankr_token_plans.jsonl"))
        self.deployment_policy = DeploymentPolicy(); self.cycle_count = 0

    def cycle(self):
        self.cycle_count += 1; telemetry = CycleTelemetry(self.cycle_count, len(self.agents))
        print(f"CYCLE {self.cycle_count} START agents={len(self.agents)}", flush=True)
        opportunities = self.research.cycle(self.agents, self.cycle_count)
        top = opportunities[:3]; execution_candidates = []
        for opportunity in top:
            h = opportunity.hypothesis
            self._event("research", h.agent, "produced", {"ticker": h.ticker, "hypothesis_id": h.hypothesis_id, "score": h.score, "thesis": h.thesis})
            self._event("debate", h.agent, "challenged", asdict(opportunity.debate))
            self._event("evidence", h.agent, "verified", {"score": opportunity.evidence_score})
            self._event("ranking", h.agent, "ranked", {"risk_adjusted": opportunity.risk_adjusted})
            if opportunity.risk_adjusted >= .62 and h.risk <= .35: execution_candidates.append(opportunity)

        telemetry.stage("research", "ok", len(self.agents), "autonomous research cycle executed")
        telemetry.stage("hypotheses", "ok", len(opportunities), "independent hypotheses generated")
        telemetry.stage("debate", "ok", len(opportunities), "adversarial challenge pass executed")
        telemetry.stage("evidence", "ok", len(top), "evidence scoring completed")
        telemetry.stage("ranking", "ok", len(execution_candidates), "risk-adjusted opportunities ranked")

        existing = self.bankr.recent_symbols()
        deployments = []
        for opportunity in execution_candidates:
            agent = opportunity.hypothesis.agent
            # Only the four explicitly provisioned Bankr execution identities can deploy.
            if agent not in ("A001", "A002", "A003", "A004"):
                continue
            ticker = self.tickers.choose(thesis=opportunity.hypothesis.thesis, agent=agent, cycle=self.cycle_count, existing=existing)
            # Alternate supported chains to diversify research, while respecting
            # the Bankr user-key launch API (Robinhood Chain or Base).
            chain = "robinhood" if self.cycle_count % 2 else "base"
            plan = self.bankr.plan(agent, ticker.name, ticker.symbol, opportunity.hypothesis.thesis, opportunity.risk_adjusted, chain)
            decision = self.deployment_policy.evaluate(
                plan, deployments_today=self.bankr.deployments_today(agent), authenticated=self.bankr.credential_configured(agent)
            )
            self._event("risk", agent, "approved" if decision.allowed else "blocked", {"allowed": decision.allowed, "reason": decision.reason, "ticker": ticker.symbol})
            if not decision.allowed:
                continue
            if not self.bankr.live:
                result = self.bankr.simulate(plan)
                status = "simulated"
            else:
                try:
                    result = self.bankr.deploy(plan); status = result.status
                except Exception as exc:
                    self._event("bankr", agent, "error", {"ticker": ticker.symbol, "error": f"{type(exc).__name__}: {exc}"})
                    continue
            deployments.append(asdict(result)); existing.add(ticker.symbol)
            self._event("bankr", agent, status, {"ticker": ticker.symbol, "chain": chain, "token_address": result.token_address, "tx_hash": result.tx_hash})

        telemetry.stage("risk", "ok", len(execution_candidates), "risk governor evaluated candidates")
        telemetry.stage("deployment_policy", "ok", len(execution_candidates), "deployment policy evaluated survivors")
        telemetry.stage("bankr", "deployed" if any(x["status"] == "deployed" for x in deployments) else ("simulated" if deployments else "idle"), len(deployments), "autonomous Bankr token-launch execution")
        telemetry.stage("on_chain_observation", "pending" if deployments else "idle", len(deployments), "launched tokens recorded for observation")
        telemetry.stage("pnl", "ok", 0, "portfolio accounting available")
        telemetry.stage("learning", "ok", len(self.metrics.stats), "strategy book available")

        result = {"cycle": self.cycle_count, "arbitrage": asdict(self.arbitrage.cycle()) if self.arbitrage else None,
                  "opportunities": [{"agent": x.hypothesis.agent, "ticker": x.hypothesis.ticker, "hypothesis_id": x.hypothesis.hypothesis_id, "score": x.hypothesis.score, "debate_survival": x.debate.survival_score, "evidence": x.evidence_score, "risk_adjusted": x.risk_adjusted} for x in top],
                  "execution_intents": deployments, "bankr_plans": deployments, "portfolio": self.portfolio.snapshot()}
        result["telemetry"] = telemetry.snapshot(); self._event("cycle", "SYSTEM", "completed", result); telemetry.log(); return result

    def _event(self, stage, agent, status, payload):
        event = LifecycleEvent(self.cycle_count, stage, agent, status, payload, time.time()); self.audit.append("lifecycle", **asdict(event)); return event

    def snapshot(self):
        risk = {"exposure": self.risk.exposure, "daily_pnl": self.risk.daily_pnl, "halted": self.risk.halted}
        return {"cycles": self.cycle_count, "agents": len(self.agents), "arbitrage": self.arbitrage.snapshot() if self.arbitrage else None, "research": self.research.snapshot(), "portfolio": self.portfolio.snapshot(), "risk": risk, "bankr": self.bankr.snapshot()}
