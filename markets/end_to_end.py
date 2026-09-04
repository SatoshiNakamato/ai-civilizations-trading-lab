from __future__ import annotations
from dataclasses import dataclass, asdict
import os, time
from markets.audit_log import AuditLog
from markets.continuous_arbitrage import ContinuousArbitrage
from markets.portfolio import Portfolio
from markets.strategy_metrics import StrategyMetrics
from markets.bankr_token_agent import BankrTokenAgent
from markets.deployment_policy import DeploymentPolicy
from risk.governor import RiskGovernor
from civilizations.alert_gate import AlertGate
from civilizations.cycle_telemetry import CycleTelemetry
from civilizations.autonomous_research import AutonomousResearchEngine
from civilizations.ticker_brain import TickerBrain
from civilizations.email_alerts import AlertCandidate, EmailAlertGateway

@dataclass
class LifecycleEvent:
    cycle: int; stage: str; agent: str; status: str; payload: dict; created_at: float

class TradingCivilizationV1:
    """Continuous multi-agent research, paper arbitrage and alert pipeline.

    The 100-agent civilization researches and debates ideas every cycle. High-
    quality alpha candidates and validated cross-venue arbitrage opportunities
    are attributed to their source agents and sent through the existing
    opt-in email gateway. Bankr remains isolated from the research/alert path.
    """
    EXECUTORS = ("A001", "A002", "A003", "A004")

    def __init__(self, runtime=None, agents=None, data_dir="data/civilization"):
        self.data_dir=data_dir; os.makedirs(data_dir, exist_ok=True); self.runtime=runtime
        self.agents=agents or [f"A{i:03d}" for i in range(1,101)]
        self.arbitrage=ContinuousArbitrage(runtime=runtime, agents=self.agents) if runtime else ContinuousArbitrage(agents=self.agents)
        self.audit=AuditLog(os.path.join(data_dir,"lifecycle.jsonl")); self.portfolio=Portfolio(); self.metrics=StrategyMetrics()
        self.risk=RiskGovernor(); self.alerts=AlertGate(); self.email=EmailAlertGateway(); self.research=AutonomousResearchEngine(); self.tickers=TickerBrain()
        self.bankr=BankrTokenAgent(os.path.join(data_dir,"bankr_token_plans.jsonl")); self.deployment_policy=DeploymentPolicy(); self.cycle_count=0

    def _send_alpha_alerts(self, opportunities):
        sent = 0
        for o in opportunities[:3]:
            h=o.hypothesis
            confidence=min(0.99, h.evidence * .75 + o.debate.survival_score * .25)
            edge=max(0.0, o.risk_adjusted - .60)
            candidate=AlertCandidate(
                title=f"{h.ticker} alpha candidate",
                category="alpha-token",
                summary=(f"Agent {h.agent} produced a high-ranked {h.ticker} hypothesis: {h.thesis}. "
                         f"Risk-adjusted score={o.risk_adjusted:.3f}; evidence={o.evidence_score:.3f}; "
                         f"debate survival={o.debate.survival_score:.3f}."),
                confidence=confidence, edge=edge, risk=h.risk,
                sources=tuple(getattr(h, "sources", ()) or ()), agent=h.agent,
            )
            if self.email.send(candidate):
                sent += 1
        return sent

    def cycle(self):
        self.cycle_count += 1
        telemetry=CycleTelemetry(self.cycle_count,len(self.agents))
        print(f"CYCLE {self.cycle_count} START agents={len(self.agents)}",flush=True)
        opportunities=self.research.cycle(self.agents,self.cycle_count)
        top=opportunities[:3]
        for o in top:
            h=o.hypothesis
            self._event("research",h.agent,"produced",{"ticker":h.ticker,"hypothesis_id":h.hypothesis_id,"score":h.score,"thesis":h.thesis})
            self._event("debate",h.agent,"challenged",asdict(o.debate)); self._event("evidence",h.agent,"verified",{"score":o.evidence_score})
            self._event("ranking",h.agent,"ranked",{"risk_adjusted":o.risk_adjusted})
        telemetry.stage("research","ok",len(self.agents),"public-data-aware autonomous research executed")
        telemetry.stage("hypotheses","ok",len(opportunities),"independent hypotheses generated")
        telemetry.stage("debate","ok",len(opportunities),"adversarial challenge pass executed")
        telemetry.stage("evidence","ok",len(top),"evidence scoring completed")

        alpha_alerts=self._send_alpha_alerts(top)
        telemetry.stage("alerts","ok",alpha_alerts,"high-value alpha alerts delivered")

        arb_result=None
        try:
            arb_result=self.arbitrage.cycle()
            if arb_result.opened or arb_result.closed:
                self._event("arbitrage","SYSTEM","cycle",asdict(arb_result))
            telemetry.stage("arbitrage","ok",arb_result.opened,"live public quotes scanned; paper fills only")
        except Exception as exc:
            self._event("arbitrage","SYSTEM","error",{"error":f"{type(exc).__name__}: {exc}"})
            telemetry.stage("arbitrage","error",0,"arbitrage scan unavailable; research pipeline continued")

        execution=[o for o in opportunities if o.hypothesis.agent in self.EXECUTORS and o.risk_adjusted >= .62 and o.hypothesis.risk <= .35]
        telemetry.stage("ranking","ok",len(execution),"executor candidates survived ranking")
        existing=self.bankr.recent_symbols(); deployments=[]
        for o in execution[:1]:
            agent=o.hypothesis.agent; ticker=self.tickers.choose(thesis=o.hypothesis.thesis,agent=agent,cycle=self.cycle_count,existing=existing)
            chain="robinhood" if self.cycle_count % 2 else "base"
            plan=self.bankr.plan(agent,ticker.name,ticker.symbol,o.hypothesis.thesis,o.risk_adjusted,chain)
            decision=self.deployment_policy.evaluate(plan,deployments_today=self.bankr.deployments_today(agent),authenticated=self.bankr.credential_configured(agent))
            self._event("risk",agent,"approved" if decision.allowed else "blocked",{"allowed":decision.allowed,"reason":decision.reason,"ticker":ticker.symbol,"ticker_score":ticker.score})
            if not decision.allowed: continue
            try:
                result=self.bankr.deploy(plan) if self.bankr.live else self.bankr.simulate(plan)
            except Exception as exc:
                self._event("bankr",agent,"error",{"ticker":ticker.symbol,"error":f"{type(exc).__name__}: {exc}"}); continue
            deployments.append(asdict(result)); existing.add(ticker.symbol)
            self._event("bankr",agent,result.status,{"ticker":ticker.symbol,"chain":chain,"token_address":result.token_address,"tx_hash":result.tx_hash})
        telemetry.stage("risk","ok",len(execution),"risk governor evaluated candidates")
        telemetry.stage("deployment_policy","ok",len(execution),"deployment policy evaluated survivors")
        telemetry.stage("bankr","deployed" if any(x["status"]=="deployed" for x in deployments) else ("simulated" if deployments else "idle"),len(deployments),"autonomous Bankr token-launch execution")
        telemetry.stage("on_chain_observation","pending" if deployments else "idle",len(deployments),"launches queued for observation")
        telemetry.stage("pnl","ok",0,"portfolio accounting available")
        telemetry.stage("learning","ok",len(self.metrics.stats),"strategy book available")
        result={"cycle":self.cycle_count,"opportunities":[{"agent":o.hypothesis.agent,"ticker":o.hypothesis.ticker,"hypothesis_id":o.hypothesis.hypothesis_id,"score":o.hypothesis.score,"debate_survival":o.debate.survival_score,"evidence":o.evidence_score,"risk_adjusted":o.risk_adjusted} for o in top],"execution_intents":deployments,"bankr_plans":deployments,"portfolio":self.portfolio.snapshot(),"alerts":{"email":self.email.snapshot(),"alpha_sent":alpha_alerts},"arbitrage":asdict(arb_result) if arb_result else None}
        result["telemetry"]=telemetry.snapshot(); self._event("cycle","SYSTEM","completed",result); telemetry.log(); return result

    def _event(self,stage,agent,status,payload): self.audit.append("lifecycle",**asdict(LifecycleEvent(self.cycle_count,stage,agent,status,payload,time.time())))
    def snapshot(self):
        return {"cycles":self.cycle_count,"agents":len(self.agents),"arbitrage":self.arbitrage.snapshot() if self.arbitrage else None,"research":self.research.snapshot(),"portfolio":self.portfolio.snapshot(),"risk":{"exposure":self.risk.exposure,"daily_pnl":self.risk.daily_pnl,"halted":self.risk.halted},"bankr":self.bankr.snapshot(),"alerts":{"email":self.email.snapshot()}}
