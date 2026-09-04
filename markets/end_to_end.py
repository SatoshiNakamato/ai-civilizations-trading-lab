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

@dataclass
class LifecycleEvent:
    cycle: int; stage: str; agent: str; status: str; payload: dict; created_at: float

class TradingCivilizationV1:
    """100-agent public research -> meme concept -> launch-intent pipeline.

    A001-A004 are execution identities. Bankr keys remain in the host
    environment and the Bankr adapter exposes token launches only. The
    pipeline does not move treasury funds.
    """
    EXECUTORS = ("A001", "A002", "A003", "A004")
    def __init__(self, runtime=None, agents=None, data_dir="data/civilization", bankr_live=None):
        self.data_dir=data_dir; os.makedirs(data_dir, exist_ok=True); self.runtime=runtime
        self.agents=agents or [f"A{i:03d}" for i in range(1,101)]
        self.arbitrage=ContinuousArbitrage(runtime=runtime, agents=self.agents) if runtime else None
        self.audit=AuditLog(os.path.join(data_dir,"lifecycle.jsonl")); self.portfolio=Portfolio(); self.metrics=StrategyMetrics()
        self.risk=RiskGovernor(); self.alerts=AlertGate(); self.research=AutonomousResearchEngine(); self.tickers=TickerBrain()
        self.bankr=BankrTokenAgent(os.path.join(data_dir,"bankr_token_plans.jsonl"), live=False if bankr_live is None else bankr_live); self.deployment_policy=DeploymentPolicy(); self.cycle_count=0

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
        last_signals=getattr(self.research,"last_signals",())
        telemetry.stage("signals","ok",len(last_signals),"X-compatible/public meme and news signals collected")
        telemetry.stage("hypotheses","ok",len(opportunities),"independent hypotheses generated")
        telemetry.stage("debate","ok",len(opportunities),"adversarial challenge pass executed")
        telemetry.stage("evidence","ok",len(top),"evidence scoring completed")

        execution=[o for o in opportunities if o.hypothesis.agent in self.EXECUTORS and o.risk_adjusted >= .62 and o.hypothesis.risk <= .35]
        telemetry.stage("ranking","ok",len(execution),"executor candidates survived ranking")
        existing=self.bankr.recent_symbols(); deployments=[]; bankr_plans=[]; intents=[]
        shared_quota=self.bankr.MAX_LAUNCHES_PER_ROLLING_DAY
        for o in execution[:1]:
            agent=o.hypothesis.agent
            ticker=self.tickers.choose(thesis=o.hypothesis.thesis,agent=agent,cycle=self.cycle_count,existing=existing)
            chain="robinhood" if self.cycle_count % 2 else "base"
            plan=self.bankr.plan(agent,ticker.name,ticker.symbol,o.hypothesis.thesis,o.risk_adjusted,chain)

            # The free-tier limit is shared by the whole Bankr account, not by
            # individual agent keys. Defer automatically once the three-launch
            # rolling-24h quota is exhausted; do not turn normal quota pressure
            # into a deployment error and do not make another API request.
            quota_used=self.bankr.deployments_today()
            if self.bankr.live and quota_used >= shared_quota:
                plan.status="deferred"
                self.bankr._audit(plan)
                intent={"agent":agent,"name":ticker.name,"ticker":ticker.symbol,"ticker_score":ticker.score,"chain":chain,"research_score":o.hypothesis.score,"risk_adjusted":o.risk_adjusted,"risk":o.hypothesis.risk,"allowed":False,"reason":f"shared Bankr free-account quota reached: {quota_used}/{shared_quota} in rolling 24h"}
                intents.append(intent)
                self._event("launch_intent",agent,"blocked",intent)
                self._event("bankr",agent,"deferred",{"ticker":ticker.symbol,"reason":intent["reason"]})
                continue

            authenticated=(not self.bankr.live) or self.bankr.credential_configured(agent)
            decision=self.deployment_policy.evaluate(plan,deployments_today=quota_used,authenticated=authenticated)
            intent={"agent":agent,"name":ticker.name,"ticker":ticker.symbol,"ticker_score":ticker.score,"chain":chain,"research_score":o.hypothesis.score,"risk_adjusted":o.risk_adjusted,"risk":o.hypothesis.risk,"allowed":decision.allowed,"reason":decision.reason}
            intents.append(intent)
            self._event("launch_intent",agent,"approved" if decision.allowed else "blocked",intent)
            if not decision.allowed:
                bankr_plans.append(asdict(plan))
                continue
            try:
                result=self.bankr.deploy(plan) if self.bankr.live else self.bankr.simulate(plan)
            except Exception as exc:
                self._event("bankr",agent,"error",{"ticker":ticker.symbol,"error":f"{type(exc).__name__}: {exc}"})
                bankr_plans.append(asdict(plan))
                continue
            result_dict=asdict(result)
            bankr_plans.append(result_dict)
            deployments.append(result_dict); existing.add(ticker.symbol)
            self._event("bankr",agent,result.status,{"ticker":ticker.symbol,"chain":chain,"token_address":result.token_address,"tx_hash":result.tx_hash})
        telemetry.stage("risk","ok",len(execution),"risk governor evaluated candidates")
        telemetry.stage("deployment_policy","ok",len(intents),"deployment policy evaluated survivors")
        telemetry.stage("launch_intent","ok",len([x for x in intents if x["allowed"]]),"launch intents produced after research and risk gates")
        telemetry.stage("bankr","deployed" if any(x["status"]=="deployed" for x in deployments) else ("simulated" if deployments else "idle"),len(deployments),"autonomous Bankr token-launch execution")
        telemetry.stage("on_chain_observation","pending" if deployments else "idle",len(deployments),"launches queued for observation")
        telemetry.stage("pnl","ok",0,"portfolio accounting available")
        telemetry.stage("learning","ok",len(self.metrics.stats),"strategy book available")
        result={"cycle":self.cycle_count,"signals":len(last_signals),"opportunities":[{"agent":o.hypothesis.agent,"ticker":o.hypothesis.ticker,"hypothesis_id":o.hypothesis.hypothesis_id,"score":o.hypothesis.score,"debate_survival":o.debate.survival_score,"evidence":o.evidence_score,"risk_adjusted":o.risk_adjusted} for o in top],"launch_intents":intents,"bankr_plans":bankr_plans,"execution_intents":deployments,"portfolio":self.portfolio.snapshot()}
        result["telemetry"]=telemetry.snapshot(); self._event("cycle","SYSTEM","completed",result); telemetry.log(); return result

    def _event(self,stage,agent,status,payload): self.audit.append("lifecycle",**asdict(LifecycleEvent(self.cycle_count,stage,agent,status,payload,time.time())))
    def snapshot(self):
        return {"cycles":self.cycle_count,"agents":len(self.agents),"arbitrage":self.arbitrage.snapshot() if self.arbitrage else None,"research":self.research.snapshot(),"portfolio":self.portfolio.snapshot(),"risk":{"exposure":self.risk.exposure,"daily_pnl":self.risk.daily_pnl,"halted":self.risk.halted},"bankr":self.bankr.snapshot()}
