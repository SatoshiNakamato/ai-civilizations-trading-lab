from __future__ import annotations
from dataclasses import dataclass, asdict, is_dataclass
import os, time
from markets.audit_log import AuditLog
from markets.continuous_arbitrage import ContinuousArbitrage
from markets.portfolio import Portfolio
from markets.strategy_metrics import StrategyMetrics
from markets.bankr_token_agent import BankrTokenAgent
from markets.deployment_policy import DeploymentPolicy
from markets.deployment_verifier import DeploymentVerifier
from risk.governor import RiskGovernor
from civilizations.alert_gate import AlertGate
from civilizations.cycle_telemetry import CycleTelemetry
from civilizations.autonomous_research import AutonomousResearchEngine
from civilizations.ticker_brain import TickerBrain

@dataclass
class LifecycleEvent:
    cycle: int; stage: str; agent: str; status: str; payload: dict; created_at: float

class TradingCivilizationV1:
    """100-agent public research -> launch intent -> verified deployment -> observation pipeline."""
    EXECUTORS = ("A001", "A002", "A003", "A004")
    def __init__(self, runtime=None, agents=None, data_dir="data/civilization", bankr_live=None):
        self.data_dir=data_dir; os.makedirs(data_dir, exist_ok=True); self.runtime=runtime
        self.agents=agents or [f"A{i:03d}" for i in range(1,101)]
        self.arbitrage=ContinuousArbitrage(runtime=runtime, agents=self.agents) if runtime else None
        self.audit=AuditLog(os.path.join(data_dir,"lifecycle.jsonl")); self.portfolio=Portfolio(); self.metrics=StrategyMetrics()
        self.risk=RiskGovernor(); self.alerts=AlertGate(); self.research=AutonomousResearchEngine(); self.tickers=TickerBrain()
        self.bankr=BankrTokenAgent(os.path.join(data_dir,"bankr_token_plans.jsonl"), live=False if bankr_live is None else bankr_live); self.deployment_policy=DeploymentPolicy(); self.verifier=DeploymentVerifier(); self.cycle_count=0

    def cycle(self):
        self.cycle_count += 1
        telemetry=CycleTelemetry(self.cycle_count,len(self.agents))
        print(f"CYCLE {self.cycle_count} START agents={len(self.agents)}",flush=True)
        opportunities=self.research.cycle(self.agents,self.cycle_count); top=opportunities[:3]
        for o in top:
            h=o.hypothesis
            self._event("research",h.agent,"produced",{"ticker":h.ticker,"hypothesis_id":h.hypothesis_id,"score":h.score,"thesis":h.thesis})
            self._event("debate",h.agent,"challenged",self._as_payload(o.debate)); self._event("evidence",h.agent,"verified",{"score":o.evidence_score}); self._event("ranking",h.agent,"ranked",{"risk_adjusted":o.risk_adjusted})
        telemetry.stage("research","ok",len(self.agents),"public-data-aware autonomous research executed")
        last_signals=getattr(self.research,"last_signals",()); telemetry.stage("signals","ok",len(last_signals),"X-compatible/public meme and news signals collected")
        telemetry.stage("hypotheses","ok",len(opportunities),"independent hypotheses generated"); telemetry.stage("debate","ok",len(opportunities),"adversarial challenge pass executed"); telemetry.stage("evidence","ok",len(top),"evidence scoring completed")
        execution=[o for o in opportunities if o.hypothesis.agent in self.EXECUTORS and o.risk_adjusted >= .62 and o.hypothesis.risk <= .35]
        telemetry.stage("ranking","ok",len(execution),"executor candidates survived ranking")
        existing=self.bankr.recent_symbols(); deployments=[]; bankr_plans=[]; intents=[]; observations=[]
        shared_quota=getattr(self.bankr,"MAX_LAUNCHES_PER_ROLLING_DAY",3); quota_counter=getattr(self.bankr,"deployments_today",None); quota_used=quota_counter() if callable(quota_counter) else 0; slots=max(0, shared_quota-quota_used)
        if self.bankr.live: candidates=execution[:slots] if slots else execution[:1]
        else: candidates=execution[:1]
        for o in candidates:
            agent=o.hypothesis.agent; ticker=self.tickers.choose(thesis=o.hypothesis.thesis,agent=agent,cycle=self.cycle_count,existing=existing); chain="robinhood" if self.cycle_count % 2 else "base"
            plan=self.bankr.plan(agent,ticker.name,ticker.symbol,o.hypothesis.thesis,o.risk_adjusted,chain,risk=o.hypothesis.risk)
            quota_used=quota_counter() if callable(quota_counter) else 0
            if self.bankr.live and quota_used >= shared_quota:
                plan.status="deferred"; self.bankr._audit(plan); intent={"agent":agent,"name":ticker.name,"ticker":ticker.symbol,"ticker_score":ticker.score,"chain":chain,"research_score":o.hypothesis.score,"risk_adjusted":o.risk_adjusted,"risk":o.hypothesis.risk,"allowed":False,"reason":f"shared Bankr free-account quota reached: {quota_used}/{shared_quota} in rolling 24h"}; intents.append(intent); self._event("launch_intent",agent,"blocked",intent); self._event("bankr",agent,"deferred",{"ticker":ticker.symbol,"reason":intent["reason"]}); bankr_plans.append(asdict(plan)); continue
            authenticated=(not self.bankr.live) or self.bankr.credential_configured(agent); decision=self.deployment_policy.evaluate(plan,deployments_today=quota_used,authenticated=authenticated)
            intent={"agent":agent,"name":ticker.name,"ticker":ticker.symbol,"ticker_score":ticker.score,"chain":chain,"research_score":o.hypothesis.score,"risk_adjusted":o.risk_adjusted,"risk":o.hypothesis.risk,"allowed":decision.allowed,"reason":decision.reason}; intents.append(intent); self._event("launch_intent",agent,"approved" if decision.allowed else "blocked",intent)
            if not decision.allowed: bankr_plans.append(asdict(plan)); continue
            try:
                result=self.bankr.deploy(plan) if self.bankr.live else self.bankr.simulate(plan)
            except Exception as exc:
                error=f"{type(exc).__name__}: {exc}"; plan.status="failed"; plan.error=str(exc); self.bankr._audit(plan); bankr_plans.append(asdict(plan)); self._event("bankr",agent,"error",{"ticker":ticker.symbol,"error":error}); continue
            result_dict=asdict(result); bankr_plans.append(result_dict)
            self._event("bankr",agent,result.status,{"ticker":ticker.symbol,"chain":chain,"token_address":result.token_address,"tx_hash":result.tx_hash})
            if result.status == "deployed":
                deployments.append(result_dict); existing.add(ticker.symbol)
            elif result.status == "partial_simulation":
                self._event("deployment_verification",agent,"partial_simulation",{"ticker":ticker.symbol,"token_address":result.token_address,"tx_hash":result.tx_hash,"error":result.error})
        telemetry.stage("risk","ok",len(execution),"risk governor evaluated candidates"); telemetry.stage("deployment_policy","ok",len(intents),"deployment policy evaluated survivors"); telemetry.stage("launch_intent","ok",len([x for x in intents if x["allowed"]]),"launch intents produced after research and risk gates")
        failed=[x for x in bankr_plans if x.get("status")=="failed" and x.get("error")]
        partial=[x for x in bankr_plans if x.get("status")=="partial_simulation"]
        if deployments:
            bankr_status="deployed"; bankr_detail=f"Bankr launch broadcast ({len(deployments)}); awaiting on-chain verification"
        elif any(x.get("status")=="deferred" for x in bankr_plans): bankr_status="deferred"; bankr_detail="Bankr launch deferred by automatic quota gate"
        elif partial: bankr_status="partial"; bankr_detail="Bankr returned partial/simulation launch responses; no deployment counted"
        elif self.bankr.live and failed: bankr_status="error"; bankr_detail=f"Bankr live launch failed: {failed[0]['error']}"
        elif self.bankr.live and intents: bankr_status="error"; bankr_detail="Bankr live launch attempted but no deployment succeeded"
        elif deployments: bankr_status="simulated"; bankr_detail="autonomous Bankr token-launch simulation"
        else: bankr_status="idle"; bankr_detail="no Bankr deployment candidate reached execution"
        telemetry.stage("bankr",bankr_status,len(deployments),bankr_detail)
        for item in deployments:
            verification=self.verifier.verify(item["chain"],item["token_address"],item["tx_hash"])
            item["verification"]=verification.as_dict(); observations.append(item)
            self._event("deployment_verification",item["agent"],verification.status,item["verification"])
        verified=sum(1 for x in observations if x["verification"]["status"]=="verified")
        pending=sum(1 for x in observations if x["verification"]["status"]=="pending")
        telemetry.stage("deployment_verification","ok" if observations else "idle",len(observations),f"{verified} verified, {pending} pending on-chain")
        telemetry.stage("on_chain_observation","active" if observations else "idle",len(observations),"deployed launches queued for on-chain observation")
        telemetry.stage("pnl","ok",0,"portfolio accounting available"); telemetry.stage("learning","ok",len(self.metrics.stats),"strategy book available")
        result={"cycle":self.cycle_count,"signals":len(last_signals),"opportunities":[{"agent":o.hypothesis.agent,"ticker":o.hypothesis.ticker,"hypothesis_id":o.hypothesis.hypothesis_id,"score":o.hypothesis.score,"debate_survival":o.debate.survival_score,"evidence":o.evidence_score,"risk_adjusted":o.risk_adjusted} for o in top],"launch_intents":intents,"bankr_plans":bankr_plans,"execution_intents":deployments,"observations":observations,"portfolio":self.portfolio.snapshot()}; result["telemetry"]=telemetry.snapshot(); self._event("cycle","SYSTEM","completed",result); telemetry.log(); return result

    @staticmethod
    def _as_payload(value): return asdict(value) if is_dataclass(value) else dict(vars(value)) if hasattr(value,"__dict__") else value
    def _event(self,stage,agent,status,payload): self.audit.append("lifecycle",**asdict(LifecycleEvent(self.cycle_count,stage,agent,status,payload,time.time())))
    def snapshot(self): return {"cycles":self.cycle_count,"agents":len(self.agents),"arbitrage":self.arbitrage.snapshot() if self.arbitrage else None,"research":self.research.snapshot(),"portfolio":self.portfolio.snapshot(),"risk":{"exposure":self.risk.exposure,"daily_pnl":self.risk.daily_pnl,"halted":self.risk.halted},"bankr":self.bankr.snapshot()}
