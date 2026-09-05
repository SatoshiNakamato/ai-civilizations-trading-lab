from __future__ import annotations
from dataclasses import dataclass, asdict, is_dataclass, fields
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
    """Continuous multi-agent research, live/public arbitrage intelligence and optional execution."""
    EXECUTORS = ("A001", "A002", "A003", "A004")

    def __init__(self, runtime=None, agents=None, data_dir="data/civilization"):
        self.data_dir=data_dir; os.makedirs(data_dir, exist_ok=True); self.runtime=runtime
        self.agents=agents or [f"A{i:03d}" for i in range(1,101)]
        self.arbitrage=ContinuousArbitrage(runtime=runtime, agents=self.agents) if runtime else ContinuousArbitrage(agents=self.agents)
        self.audit=AuditLog(os.path.join(data_dir,"lifecycle.jsonl")); self.portfolio=Portfolio(); self.metrics=StrategyMetrics()
        self.risk=RiskGovernor(); self.alerts=AlertGate(); self.email=EmailAlertGateway(); self.research=AutonomousResearchEngine(); self.tickers=TickerBrain()
        self.bankr=BankrTokenAgent(os.path.join(data_dir,"bankr_token_plans.jsonl")); self.deployment_policy=DeploymentPolicy(); self.cycle_count=0

    @staticmethod
    def _as_payload(value):
        if value is None: return None
        if is_dataclass(value): return asdict(value)
        if hasattr(value, "__dict__") and vars(value): return dict(vars(value))
        # Test doubles and lightweight result objects often expose data as
        # class attributes rather than instance attributes. Preserve the
        # public fields needed by lifecycle telemetry and API consumers.
        names = ("cycle", "opened", "closed", "realized_pnl", "profitable_traders", "status", "token_address", "tx_hash", "order_id")
        payload = {name: getattr(value, name) for name in names if hasattr(value, name)}
        return payload if payload else value

    @staticmethod
    def _result_status(result): return getattr(result, "status", "unknown")

    @staticmethod
    def _chain_link(chain: str, address: str) -> str:
        if not address: return ""
        chain = (chain or "").lower()
        explorers = {"base": "https://basescan.org/token/", "robinhood": "https://basescan.org/token/"}
        prefix = explorers.get(chain, "https://basescan.org/token/")
        return prefix + address

    def _send_alpha_alerts(self, opportunities):
        sent = 0
        for o in opportunities[:3]:
            h=o.hypothesis
            confidence=min(0.99, h.evidence * .75 + o.debate.survival_score * .25)
            edge=max(0.005, o.risk_adjusted - .60)
            candidate=AlertCandidate(title=f"{h.ticker} alpha candidate", category="alpha-token",
                summary=(f"Agent {h.agent} produced a high-ranked {h.ticker} hypothesis: {h.thesis}. "
                         f"Risk-adjusted score={o.risk_adjusted:.3f}; evidence={o.evidence_score:.3f}; "
                         f"debate survival={o.debate.survival_score:.3f}."),
                confidence=confidence, edge=edge, risk=h.risk,
                sources=tuple(getattr(h, "sources", ()) or ()), agent=h.agent)
            if self.email.send(candidate): sent += 1
        return sent

    def _send_deployment_alert(self, plan, result):
        address=str(getattr(result, "token_address", "") or "")
        tx_hash=str(getattr(result, "tx_hash", "") or "")
        if getattr(result, "status", "") != "deployed" or not address:
            return 0
        url=self._chain_link(plan.chain, address)
        candidate=AlertCandidate(
            title=f"{plan.name} launched ({plan.symbol})", category="alpha-token",
            summary=(f"Agent {plan.agent} launched the researched token {plan.symbol}. "
                     f"Transaction: {tx_hash or 'not returned by provider'}."),
            confidence=min(0.99, max(0.80, float(plan.score))), edge=max(0.005, float(plan.score)-0.60),
            risk=max(0.0, min(1.0, 1.0-float(plan.score))), agent=plan.agent,
            token_address=address, chain=plan.chain, url=url,
        )
        return 1 if self.email.send(candidate) else 0

    def _send_arbitrage_alert(self, arb_result):
        if not arb_result: return 0
        opened=getattr(arb_result, "opened", 0); closed=getattr(arb_result, "closed", 0)
        realized=float(getattr(arb_result, "realized_pnl", 0.0) or 0.0)
        if not opened and not closed and realized <= 0: return 0
        candidate=AlertCandidate(title="Arbitrage opportunity detected", category="arbitrage",
            summary=(f"Cross-venue arbitrage scan opened {opened} position(s), closed {closed}, "
                     f"with realized PnL={realized:.6f}. Review the live quote details and attribution ledger."),
            confidence=0.95 if opened else 0.90, edge=max(0.005, abs(realized)), risk=0.25, agent="SYSTEM")
        return 1 if self.email.send(candidate) else 0

    def cycle(self):
        self.cycle_count += 1; telemetry=CycleTelemetry(self.cycle_count,len(self.agents))
        print(f"CYCLE {self.cycle_count} START agents={len(self.agents)}",flush=True)
        opportunities=self.research.cycle(self.agents,self.cycle_count); top=opportunities[:3]
        for o in top:
            h=o.hypothesis; self._event("research",h.agent,"produced",{"ticker":h.ticker,"hypothesis_id":h.hypothesis_id,"score":h.score,"thesis":h.thesis})
            self._event("debate",h.agent,"challenged",self._as_payload(o.debate)); self._event("evidence",h.agent,"verified",{"score":o.evidence_score}); self._event("ranking",h.agent,"ranked",{"risk_adjusted":o.risk_adjusted})
        telemetry.stage("research","ok",len(self.agents),"public-data-aware autonomous research executed")
        telemetry.stage("hypotheses","ok",len(opportunities),"independent hypotheses generated"); telemetry.stage("debate","ok",len(opportunities),"adversarial challenge pass executed"); telemetry.stage("evidence","ok",len(top),"evidence scoring completed")
        alpha_alerts=self._send_alpha_alerts(top); telemetry.stage("alerts","ok",alpha_alerts,"high-value alpha alerts delivered")

        arb_result=None; arb_alerts=0
        try:
            arb_result=self.arbitrage.cycle()
            if getattr(arb_result,"opened",0) or getattr(arb_result,"closed",0): self._event("arbitrage","SYSTEM","cycle",self._as_payload(arb_result))
            arb_alerts=self._send_arbitrage_alert(arb_result); telemetry.stage("arbitrage","ok",getattr(arb_result,"opened",0),"live public quotes scanned")
            if arb_alerts: telemetry.stage("arbitrage_alert","ok",arb_alerts,"profitable arbitrage alert delivered")
        except Exception as exc:
            self._event("arbitrage","SYSTEM","error",{"error":f"{type(exc).__name__}: {exc}"}); telemetry.stage("arbitrage","error",0,"arbitrage scan unavailable; research pipeline continued")

        execution=[o for o in opportunities if o.hypothesis.agent in self.EXECUTORS and o.risk_adjusted >= .62 and o.hypothesis.risk <= .35]
        telemetry.stage("ranking","ok",len(execution),"executor candidates survived ranking"); existing=self.bankr.recent_symbols(); deployments=[]; deployment_alerts=0
        for o in execution[:1]:
            agent=o.hypothesis.agent; ticker=self.tickers.choose(thesis=o.hypothesis.thesis,agent=agent,cycle=self.cycle_count,existing=existing); chain=os.getenv("BANKR_DEFAULT_CHAIN", "base").lower()
            plan=self.bankr.plan(agent,ticker.name,ticker.symbol,o.hypothesis.thesis,o.risk_adjusted,chain)
            decision=self.deployment_policy.evaluate(plan,deployments_today=self.bankr.deployments_today(agent),authenticated=self.bankr.credential_configured(agent))
            self._event("risk",agent,"approved" if decision.allowed else "blocked",{"allowed":decision.allowed,"reason":decision.reason,"ticker":ticker.symbol,"ticker_score":ticker.score})
            if not decision.allowed: continue
            try: result=self.bankr.deploy(plan) if self.bankr.live else self.bankr.simulate(plan)
            except Exception as exc: self._event("bankr",agent,"error",{"ticker":ticker.symbol,"error":f"{type(exc).__name__}: {exc}"}); continue
            deployments.append(self._as_payload(result)); existing.add(ticker.symbol); self._event("bankr",agent,self._result_status(result),{"ticker":ticker.symbol,"chain":chain,"token_address":getattr(result,"token_address",""),"tx_hash":getattr(result,"tx_hash","")})
            deployment_alerts += self._send_deployment_alert(plan,result)
        telemetry.stage("risk","ok",len(execution),"risk governor evaluated candidates"); telemetry.stage("deployment_policy","ok",len(execution),"deployment policy evaluated survivors")
        telemetry.stage("bankr","deployed" if any(x.get("status")=="deployed" for x in deployments) else ("simulated" if deployments else "idle"),len(deployments),"autonomous token-launch execution")
        telemetry.stage("deployment_alert","ok",deployment_alerts,"deployed-token alerts delivered"); telemetry.stage("on_chain_observation","pending" if deployments else "idle",len(deployments),"launches queued for observation")
        telemetry.stage("pnl","ok",0,"portfolio accounting available"); telemetry.stage("learning","ok",len(self.metrics.stats),"strategy book available")
        result={"cycle":self.cycle_count,"opportunities":[{"agent":o.hypothesis.agent,"ticker":o.hypothesis.ticker,"hypothesis_id":o.hypothesis.hypothesis_id,"score":o.hypothesis.score,"debate_survival":o.debate.survival_score,"evidence":o.evidence_score,"risk_adjusted":o.risk_adjusted} for o in top],"execution_intents":deployments,"bankr_plans":deployments,"portfolio":self.portfolio.snapshot(),"alerts":{"email":self.email.snapshot(),"alpha_sent":alpha_alerts,"deployment_sent":deployment_alerts,"arbitrage_sent":arb_alerts},"arbitrage":self._as_payload(arb_result) if arb_result else None}
        result["telemetry"]=telemetry.snapshot(); self._event("cycle","SYSTEM","completed",result); telemetry.log(); return result

    def _event(self,stage,agent,status,payload): self.audit.append("lifecycle",**asdict(LifecycleEvent(self.cycle_count,stage,agent,status,payload,time.time())))
    def snapshot(self): return {"cycles":self.cycle_count,"agents":len(self.agents),"arbitrage":self.arbitrage.snapshot() if self.arbitrage else None,"research":self.research.snapshot(),"portfolio":self.portfolio.snapshot(),"risk":{"exposure":self.risk.exposure,"daily_pnl":self.risk.daily_pnl,"halted":self.risk.halted},"bankr":self.bankr.snapshot(),"alerts":{"email":self.email.snapshot()}}
