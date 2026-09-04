from __future__ import annotations
from dataclasses import dataclass
from time import time
import re
from .core import Civilization
from .knowledge_graph import KnowledgeGraph
from .research_coordinator import ResearchCoordinator
from .research_quality import ResearchQuality
from .contradictions import ContradictionDetector
from .fallback_search import DuckDuckGoFallback
from .you_mcp import YouMCPResearch
from .email_alerts import AlertCandidate, EmailAlertGateway
from .opportunities import Opportunity, OpportunityEngine
from .research_budget import ResearchBudget
from markets.bankr_token_agent import BankrTokenAgent

@dataclass
class ResearchRuntimeStats:
    submitted:int=0; deduplicated:int=0; completed:int=0; failed:int=0
    retried:int=0; fallback_calls:int=0; cache_hits:int=0; provider_calls:int=0
    promoted:int=0; rejected:int=0; contradictions:int=0; alerts_sent:int=0
    opportunities_discovered:int=0; opportunities_validated:int=0; opportunities_rejected:int=0
    bankr_launches:int=0; bankr_failures:int=0

class ResearchRuntime:
    """Fault-tolerant, budgeted research layer around the civilization loop."""
    def __init__(self,civilization: Civilization|None=None,researcher: YouMCPResearch|None=None,fallback: DuckDuckGoFallback|None=None,alerts: EmailAlertGateway|None=None,opportunities: OpportunityEngine|None=None,budget: ResearchBudget|None=None,bankr: BankrTokenAgent|None=None):
        self.civilization=civilization or Civilization(); self.coordinator=ResearchCoordinator()
        self.researcher=researcher or YouMCPResearch(); self.fallback=fallback or DuckDuckGoFallback()
        self.knowledge_graph=KnowledgeGraph(); self.quality=ResearchQuality(); self.contradictions=ContradictionDetector()
        self.alerts=alerts or EmailAlertGateway(); self.opportunities=opportunities or OpportunityEngine()
        self.budget=budget or ResearchBudget(daily_limit=self.researcher.daily_limit, arbitrage_limit=min(50, self.researcher.daily_limit))
        self.bankr=bankr or BankrTokenAgent()
        self.stats=ResearchRuntimeStats(); self.failures=[]; self.alert_candidates=[]; self.opportunity_candidates=[]; self.bankr_launches=[]; self.started_at=time()

    def queue_agent_requests(self):
        before_count=len(self.coordinator.tasks)
        for agent in self.civilization.agents.values():
            question=self.civilization._research_query(agent); before=len(self.coordinator.tasks)
            self.coordinator.submit(question,agent.agent_id,agent.archetype,agent.curiosity); self.stats.submitted+=1
            if len(self.coordinator.tasks)==before: self.stats.deduplicated+=1
        return {'new_tasks':len(self.coordinator.tasks)-before_count,'coordinator':self.coordinator.snapshot()}

    def _share(self,task,results,source='you.com',assessment=None):
        finding_id=f'research:{task.task_id}'
        payload={'question':task.question,'topic':task.topic,'requester':task.requester,'source_provider':source,'assessment':assessment or {},'results':[r.__dict__ if hasattr(r,'__dict__') else dict(r) for r in results],'created_at':time()}
        self.knowledge_graph.add(finding_id,'research',payload); self.knowledge_graph.add(f'agent:{task.requester}','agent'); self.knowledge_graph.link(f'agent:{task.requester}',finding_id,'researched')
        snippets=[getattr(r,'snippet','') for r in results if getattr(r,'snippet','')]
        if snippets:
            self.contradictions.compare(task.topic,snippets); self.stats.contradictions=self.contradictions.snapshot()['count']

    def _fallback(self, task, source='budget-fallback'):
        results=self.fallback.search(task.question); self.stats.fallback_calls+=1
        return results, source

    def _execute(self,task):
        cached=self.researcher.cached(task.question)
        if cached is not None: self.stats.cache_hits+=1; return cached,'cache'
        if not self.budget.reserve(task.topic): return self._fallback(task)
        if not self.researcher.can_search(): return self._fallback(task, 'limit-fallback')
        try:
            results=self.researcher.search(task.question); self.stats.provider_calls+=1; return results,'you.com'
        except Exception:
            self.stats.retried+=1
            if not self.budget.reserve(task.topic): return self._fallback(task)
            try:
                results=self.researcher.search(task.question+' latest'); self.stats.provider_calls+=1; return results,'you.com-retry'
            except Exception:
                return self._fallback(task, 'duckduckgo-fallback')

    @staticmethod
    def _estimated_edge(text: str) -> float:
        matches = re.findall(r'(?:spread|edge|difference|mispricing)[^%]{0,80}(\d+(?:\.\d+)?)\s*%', text, flags=re.I)
        return max((float(x) / 100 for x in matches), default=0.0)

    def _maybe_alert(self,task,assessment,results):
        if task.topic not in {'arbitrage','market','macro','prediction','risk','alpha','research','arb'}: return
        confidence=float(assessment.get('confidence',0.0)); evidence=int(assessment.get('evidence_count',0))
        text=' '.join(getattr(r,'snippet','') for r in results)
        edge=self._estimated_edge(text)
        is_arbitrage = task.topic in {'arbitrage','arb'} and any(x in text.lower() for x in ('arbitrage','spread','mispricing','price difference'))
        category='arbitrage' if is_arbitrage else task.topic
        candidate=AlertCandidate(title=task.question[:120],category=category,summary=f'{evidence} source-backed result(s) found for: {task.question}',confidence=confidence,edge=edge,sources=tuple(getattr(r,'url','') for r in results if getattr(r,'url',''))[:5],agent=task.requester)
        self.alert_candidates.append({**candidate.__dict__,'severity':candidate.severity})
        if self.alerts.send(candidate): self.stats.alerts_sent+=1
        if is_arbitrage:
            opportunity=Opportunity(opportunity_id='',category='arbitrage',asset=task.question[:80],summary=task.question,confidence=confidence,risk=0.50,gross_edge=edge,liquidity=1.0,sources=list(candidate.sources),agents=[task.requester])
            found=self.opportunities.discover(opportunity)
            if found is not None:
                self.stats.opportunities_discovered+=1
                validated=self.opportunities.validate(found)
                if validated.status == 'validated': self.stats.opportunities_validated+=1
                else: self.stats.opportunities_rejected+=1
                self.opportunity_candidates.append({**validated.__dict__,'net_edge':validated.net_edge,'alert':self.opportunities.should_alert(validated)})

    def drain(self,max_tasks=10):
        processed=[]
        for _ in range(max(0,int(max_tasks))):
            task=self.coordinator.next_task()
            if task is None: break
            try:
                results,source=self._execute(task)
                usable=[r for r in results if getattr(r,'url','') and getattr(r,'snippet','')]
                assessment={'confidence':round(min(1.0,len(usable)/3),3),'quality':round(min(1.0,len(usable)/3),3),'evidence_count':len(usable),'promote':bool(usable),'reasons':['source_backed'] if usable else ['empty_or_unverified']}
                if not assessment['promote']: self.stats.rejected+=1; raise RuntimeError('research result rejected: insufficient source-backed evidence')
                self._share(task,results,source,assessment); self.stats.promoted+=1
                self._maybe_alert(task,assessment,results)
                self.coordinator.complete(task.task_id,f'research-results:{len(results)}'); self.stats.completed+=1; processed.append(task)
            except Exception as exc:
                task.status='failed'; self.stats.failed+=1
                self.failures.append({'task_id':task.task_id,'question':task.question,'requester':task.requester,'error':f'{type(exc).__name__}: {exc}','at':time()})
        return processed

    def cycle(self,max_research_tasks=10):
        queued=self.queue_agent_requests(); drained=self.drain(max_research_tasks); state=self.civilization.step()
        # Deployment happens only after the civilization has researched,
        # validated, ranked and marked candidates as passed. The Bankr layer
        # can only reach /token-launches/deploy; it has no wallet transfer,
        # swap, sign or submit methods. Live mode is opt-in via host env vars.
        launched=self.bankr.autonomous_deploy(self.civilization, cycle=state['tick'], max_deploys=4)
        self.bankr_launches.extend({**p.__dict__,'bankr_slot':self.bankr.agent_slot(p.agent)} for p in launched)
        self.stats.bankr_launches += len(launched)
        return {'civilization':state,'research_runtime':{'coordinator':self.coordinator.snapshot(),'stats':self.stats.__dict__.copy(),'drained':len(drained),'queued_before_cycle':queued,'knowledge_graph':self.knowledge_graph.snapshot(),'quality':self.quality.snapshot(),'contradictions':self.contradictions.snapshot(),'failures':self.failures[-20:],'alerts':self.alert_candidates[-20:],'opportunities':self.opportunity_candidates[-20:],'opportunity_engine':self.opportunities.snapshot(),'email':self.alerts.snapshot(),'you':self.researcher.snapshot(),'budget':self.budget.snapshot(),'bankr':{**self.bankr.snapshot(),'launches':self.bankr_launches[-20:]}}}

    def snapshot(self):
        return {'coordinator':self.coordinator.snapshot(),'stats':self.stats.__dict__.copy(),'knowledge_graph':self.knowledge_graph.snapshot(),'quality':self.quality.snapshot(),'contradictions':self.contradictions.snapshot(),'failures':self.failures[-20:],'alerts':self.alert_candidates[-20:],'opportunities':self.opportunity_candidates[-20:],'opportunity_engine':self.opportunities.snapshot(),'email':self.alerts.snapshot(),'you':self.researcher.snapshot(),'budget':self.budget.snapshot(),'bankr':{**self.bankr.snapshot(),'launches':self.bankr_launches[-20:]},'civilization':self.civilization.snapshot()}
