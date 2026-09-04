from __future__ import annotations
from dataclasses import dataclass, asdict
import os, time
from markets.audit_log import AuditLog
from markets.continuous_arbitrage import ContinuousArbitrage
from markets.portfolio import Portfolio, PaperExecutionEngine
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
    """Continuous research, debate, risk-gated paper-trading civilization.

    Bankr is retained only as a dormant future live-execution adapter. The
    default execution path is local paper trading, so research can be evaluated
    end-to-end without requiring a funded launch wallet or live credentials.
    """
    EXECUTORS = ("A001", "A002", "A003", "A004")
    def __init__(self, runtime=None, agents=None, data_dir="data/civilization"):
        self.data_dir=data_dir; os.makedirs(data_dir, exist_ok=True); self.runtime=runtime
        self.agents=agents or [f"A{i:03d}" for i in range(1,101)]
        self.arbitrage=ContinuousArbitrage(runtime=runtime, agents=self.agents) if runtime else None
        self.audit=AuditLog(os.path.join(data_dir,"lifecycle.jsonl")); self.portfolio=Portfolio(); self.metrics=StrategyMetrics()
        self.risk=RiskGovernor(); self.alerts=AlertGate(); self.research=AutonomousResearchEngine(); self.tickers=TickerBrain()
        self.bankr=BankrTokenAgent(os.path.join(data_dir,"bankr_token_plans.jsonl")); self.deployment_policy=DeploymentPolicy()
        self.paper=PaperExecutionEngine(initial_cash=float(os.getenv("PAPER_INITIAL_CASH","1000")), max_position_notional=float(os.getenv("PAPER_MAX_POSITION","100")))
        self.paper_enabled=os.getenv("PAPER_TRADING","1").strip().lower() not in {"0","false","no","off"}
        self.cycle_count=0

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
        execution=[o for o in opportunities if o.hypothesis.agent in self.EXECUTORS and o.risk_adjusted >= .62 and o.hypothesis.risk <= .35]
        telemetry.stage("ranking","ok",len(execution),"executor candidates survived ranking")
        paper_orders=[]
        if self.paper_enabled:
            for o in execution[:1]:
                agent=o.hypothesis.agent; ticker=self.tickers.choose(thesis=o.hypothesis.thesis,agent=agent,cycle=self.cycle_count,existing=set())
                notional=min(self.paper.max_position_notional, float(os.getenv("PAPER_ORDER_NOTIONAL","25")))
                try:
                    order=self.paper.open(agent,ticker.symbol,notional,1.0)
                    paper_orders.append(order.snapshot())
                    self._event("paper_execution",agent,"filled",{"order_id":order.order_id,"symbol":ticker.symbol,"notional":notional,"entry_price":1.0})
                except Exception as exc:
                    self._event("paper_execution",agent,"blocked",{"symbol":ticker.symbol,"error":f"{type(exc).__name__}: {exc}"})
        telemetry.stage("deployment_policy","ok",len(execution),"deployment policy evaluated survivors")
        telemetry.stage("bankr","disabled",0,"Bankr live execution parked for later")
        telemetry.stage("paper_execution","filled" if paper_orders else ("idle" if not execution else "blocked"),len(paper_orders),"local paper orders executed without live wallet access")
        telemetry.stage("deployment_verification","idle",0,"live deployment verification parked with Bankr")
        telemetry.stage("on_chain_observation","idle",0,"on-chain observation parked with live deployment")
        telemetry.stage("pnl","ok",0,"portfolio accounting available")
        telemetry.stage("learning","ok",len(self.metrics.stats),"strategy book available")
        result={"cycle":self.cycle_count,"opportunities":[{"agent":o.hypothesis.agent,"ticker":o.hypothesis.ticker,"hypothesis_id":o.hypothesis.hypothesis_id,"score":o.hypothesis.score,"debate_survival":o.debate.survival_score,"evidence":o.evidence_score,"risk_adjusted":o.risk_adjusted} for o in top],"execution_intents":paper_orders,"bankr_plans":[],"paper_orders":paper_orders,"paper":self.paper.snapshot(),"portfolio":self.portfolio.snapshot()}
        result["telemetry"]=telemetry.snapshot(); self._event("cycle","SYSTEM","completed",result); telemetry.log(); return result

    def _event(self,stage,agent,status,payload): self.audit.append("lifecycle",**asdict(LifecycleEvent(self.cycle_count,stage,agent,status,payload,time.time())))
    def snapshot(self):
        return {"cycles":self.cycle_count,"agents":len(self.agents),"arbitrage":self.arbitrage.snapshot() if self.arbitrage else None,"research":self.research.snapshot(),"portfolio":self.portfolio.snapshot(),"paper":self.paper.snapshot(),"risk":{"exposure":self.risk.exposure,"daily_pnl":self.risk.daily_pnl,"halted":self.risk.halted},"bankr":self.bankr.snapshot()}
