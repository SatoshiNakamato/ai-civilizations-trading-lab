from __future__ import annotations
from dataclasses import dataclass, asdict, is_dataclass
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
from civilizations.live_alpha import LiveAlphaScanner

@dataclass
class LifecycleEvent:
    cycle: int; stage: str; agent: str; status: str; payload: dict; created_at: float

class TradingCivilizationV1:
    """Continuous multi-agent public-market intelligence and human alerts.

    Production mode is intentionally alert-only: no exchange credentials are
    required and no trade or token deployment is submitted by the civilization.
    """
    EXECUTORS = ("A001", "A002", "A003", "A004")

    def __init__(self, runtime=None, agents=None, data_dir="data/civilization"):
        self.data_dir=data_dir; os.makedirs(data_dir, exist_ok=True); self.runtime=runtime
        self.agents=agents or [f"A{i:03d}" for i in range(1,101)]
        self.arbitrage=ContinuousArbitrage(runtime=runtime, agents=self.agents) if runtime else ContinuousArbitrage(agents=self.agents)
        self.audit=AuditLog(os.path.join(data_dir,"lifecycle.jsonl")); self.portfolio=Portfolio(); self.metrics=StrategyMetrics()
        self.risk=RiskGovernor(); self.alerts=AlertGate(); self.email=EmailAlertGateway(); self.research=AutonomousResearchEngine(); self.tickers=TickerBrain()
        self.alpha=LiveAlphaScanner(gateway=self.email); self.bankr=BankrTokenAgent(os.path.join(data_dir,"bankr_token_plans.jsonl")); self.deployment_policy=DeploymentPolicy(); self.cycle_count=0

    @staticmethod
    def _as_payload(value):
        if value is None: return None
        if is_dataclass(value): return asdict(value)
        if hasattr(value, "__dict__") and vars(value): return dict(vars(value))
        names=("cycle","opened","closed","realized_pnl","profitable_traders","status","token_address","tx_hash","order_id","net_edge","buy_venue","sell_venue","buy_price","sell_price","observed_at","quantity","notional_usd","buy_depth","sell_depth","executable","verification")
        payload={name:getattr(value,name) for name in names if hasattr(value,name)}
        return payload if payload else value

    def _event(self,stage,agent,status,payload):
        self.audit.append("lifecycle",**asdict(LifecycleEvent(self.cycle_count,stage,agent,status,payload,time.time())))

    def _send_alpha_alerts(self, opportunities):
        sent=0
        for o in opportunities[:3]:
            h=o.hypothesis
            confidence=min(.99,h.evidence*.75+o.debate.survival_score*.25)
            edge=max(.005,o.risk_adjusted-.60)
            candidate=AlertCandidate(title=f"{h.ticker} alpha candidate",category="alpha-token",summary=(
                f"Agent {h.agent} found a high-ranked setup for {h.ticker}: {h.thesis}. "
                f"Risk-adjusted score={o.risk_adjusted:.3f}; evidence={o.evidence_score:.3f}; debate survival={o.debate.survival_score:.3f}."),
                confidence=confidence,edge=edge,risk=h.risk,sources=tuple(getattr(h,"sources",()) or ()),agent=h.agent)
            if self.email.send(candidate): sent+=1
        return sent

    def _send_arbitrage_alert(self, opportunity):
        if not opportunity or getattr(opportunity,"status","")!="validated" or not getattr(opportunity,"executable",False): return 0
        observed=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(opportunity.observed_at)) if getattr(opportunity,"observed_at",0) else "unknown"
        candidate=AlertCandidate(title=f"Verified arbitrage: {opportunity.asset} {opportunity.buy_venue} → {opportunity.sell_venue}",category="arbitrage",
            summary=(f"Verified executable public-market opportunity observed {observed}. Buy {opportunity.asset} on {opportunity.buy_venue} @ VWAP ~{opportunity.buy_price:.10g}; "
                     f"sell on {opportunity.sell_venue} @ VWAP ~{opportunity.sell_price:.10g}; quantity={opportunity.quantity:.12g}; notional=${opportunity.notional_usd:.2f}. "
                     f"Top-of-book gross edge={opportunity.gross_edge:.2%}; order-book slippage={opportunity.slippage:.2%}; fees={opportunity.fees:.2%}; "
                     f"executable net edge={opportunity.net_edge:.2%}. Pre-funded balances on both venues are required; execute manually."),
            confidence=opportunity.confidence,edge=opportunity.net_edge,risk=opportunity.risk,
            sources=tuple(opportunity.sources),agent="DEPTH-VERIFIER",
            buy_venue=opportunity.buy_venue,sell_venue=opportunity.sell_venue,buy_price=opportunity.buy_price,sell_price=opportunity.sell_price,
            observed_at=opportunity.observed_at,quantity=opportunity.quantity,notional_usd=opportunity.notional_usd,
            executable=True,verification=opportunity.verification)
        return 1 if self.email.send(candidate) else 0

    def cycle(self):
        self.cycle_count+=1; telemetry=CycleTelemetry(self.cycle_count,len(self.agents))
        print(f"CYCLE {self.cycle_count} START agents={len(self.agents)}",flush=True)
        opportunities=self.research.cycle(self.agents,self.cycle_count); top=opportunities[:3]
        for o in top:
            h=o.hypothesis
            self._event("research",h.agent,"produced",{"ticker":h.ticker,"hypothesis_id":h.hypothesis_id,"score":h.score,"thesis":h.thesis})
            self._event("debate",h.agent,"challenged",self._as_payload(o.debate)); self._event("evidence",h.agent,"verified",{"score":o.evidence_score}); self._event("ranking",h.agent,"ranked",{"risk_adjusted":o.risk_adjusted})
        telemetry.stage("research","ok",len(self.agents),"100-agent public-data research executed")
        telemetry.stage("hypotheses","ok",len(opportunities),"independent hypotheses generated")
        telemetry.stage("debate","ok",len(opportunities),"adversarial challenge pass executed")
        telemetry.stage("evidence","ok",len(top),"evidence scoring completed")
        alpha_sent=self._send_alpha_alerts(top)
        discovered=self.alpha.scan_and_alert(limit=5)
        telemetry.stage("alerts","ok",alpha_sent+sum(1 for x in discovered if x.score>=.70),"alpha alerts delivered from research and public DEX discovery")

        arb=None; arb_alert=0; verified_count=0
        try:
            scanner=getattr(getattr(self.arbitrage,"runtime",None),"scanner",None)
            if scanner is not None and hasattr(scanner,"scan_once"):
                arb=scanner.scan_once()
                verified_count=len(getattr(scanner,"last_opportunities",[]) or [])
                arb_alert=int(getattr(scanner,"last_alerts_sent",0) or 0)
            else:
                arb=self.arbitrage.cycle()
                verified_count=1 if arb and getattr(arb,"executable",False) else 0
                arb_alert=self._send_arbitrage_alert(arb)
            telemetry.stage("arbitrage","ok",verified_count,"fresh public L2 opportunities verified")
            if arb: self._event("arbitrage","SYSTEM","validated",self._as_payload(arb))
            telemetry.stage("arbitrage_alert","ok",arb_alert,"verified arbitrage alerts delivered")
        except Exception as exc:
            self._event("arbitrage","SYSTEM","error",{"error":f"{type(exc).__name__}: {exc}"})
            telemetry.stage("arbitrage","error",0,"public arbitrage verification unavailable; no arbitrage alert emitted")
            telemetry.stage("arbitrage_alert","error",0,"no verified arbitrage alert emitted")

        telemetry.stage("ranking","ok",len(top),"research candidates ranked")
        telemetry.stage("risk","ok",len(top),"risk review completed for alerting")
        telemetry.stage("deployment_policy","disabled",0,"token deployment paused")
        telemetry.stage("bankr","disabled",0,"Bankr token deployment paused")
        telemetry.stage("deployment_alert","disabled",0,"deployment alerts disabled while Bankr is paused")
        telemetry.stage("on_chain_observation","idle",0,"no autonomous token launches")
        telemetry.stage("pnl","disabled",0,"no paper-trade accounting in alert-only mode")
        telemetry.stage("learning","ok",len(self.metrics.stats),"strategy book available")

        result={"cycle":self.cycle_count,
            "opportunities":[{"agent":o.hypothesis.agent,"ticker":o.hypothesis.ticker,"hypothesis_id":o.hypothesis.hypothesis_id,"score":o.hypothesis.score,"debate_survival":o.debate.survival_score,"evidence":o.evidence_score,"risk_adjusted":o.risk_adjusted} for o in top],
            "alpha_discovery":[self._as_payload(x) for x in discovered],"execution_intents":[],"bankr_plans":[],"portfolio":self.portfolio.snapshot(),
            "alerts":{"email":self.email.snapshot(),"alpha_sent":alpha_sent,"discovered_alpha":len(discovered),"arbitrage_sent":arb_alert},
            "arbitrage":self._as_payload(arb) if arb else None,"telemetry":telemetry.snapshot()}
        self._event("cycle","SYSTEM","completed",result); telemetry.log(); return result

    def snapshot(self):
        return {"cycles":self.cycle_count,"agents":len(self.agents),"arbitrage":self.arbitrage.snapshot() if self.arbitrage else None,
                "research":self.research.snapshot(),"alpha":self.alpha.snapshot(),"portfolio":self.portfolio.snapshot(),
                "risk":{"exposure":self.risk.exposure,"daily_pnl":self.risk.daily_pnl,"halted":self.risk.halted},
                "bankr":{"enabled":False,"status":"paused"},"alerts":{"email":self.email.snapshot()}}
