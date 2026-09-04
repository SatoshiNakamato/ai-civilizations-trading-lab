from __future__ import annotations
from dataclasses import dataclass
from time import time
from .core import Civilization
from .knowledge_graph import KnowledgeGraph
from .research_coordinator import ResearchCoordinator
from .research_quality import ResearchQuality
from .contradictions import ContradictionDetector
from .fallback_search import DuckDuckGoFallback
from .you_mcp import YouMCPResearch
from .email_alerts import AlertCandidate, EmailAlertGateway

@dataclass
class ResearchRuntimeStats:
    submitted:int=0; deduplicated:int=0; completed:int=0; failed:int=0
    retried:int=0; fallback_calls:int=0; cache_hits:int=0; provider_calls:int=0
    promoted:int=0; rejected:int=0; contradictions:int=0; alerts_sent:int=0

class ResearchRuntime:
    """Fault-tolerant, budgeted research layer around the civilization loop."""
    def __init__(self,civilization: Civilization|None=None,researcher: YouMCPResearch|None=None,fallback: DuckDuckGoFallback|None=None,alerts: EmailAlertGateway|None=None):
        self.civilization=civilization or Civilization(); self.coordinator=ResearchCoordinator()
        self.researcher=researcher or YouMCPResearch(); self.fallback=fallback or DuckDuckGoFallback()
        self.knowledge_graph=KnowledgeGraph(); self.quality=ResearchQuality(); self.contradictions=ContradictionDetector()
        self.alerts=alerts or EmailAlertGateway()
        self.stats=ResearchRuntimeStats(); self.failures=[]; self.alert_candidates=[]; self.started_at=time()

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

    def _execute(self,task):
        cached=self.researcher.cached(task.question)
        if cached is not None: self.stats.cache_hits+=1; return cached,'cache'
        if not self.researcher.can_search(): raise RuntimeError('You.com free MCP daily search limit reached')
        try:
            results=self.researcher.search(task.question); self.stats.provider_calls+=1; return results,'you.com'
        except Exception as first_error:
            self.stats.retried+=1
            try:
                results=self.researcher.search(task.question+' latest'); self.stats.provider_calls+=1; return results,'you.com-retry'
            except Exception as retry_error:
                results=self.fallback.search(task.question); self.stats.fallback_calls+=1; return results,'duckduckgo-fallback'

    def _maybe_alert(self,task,assessment,results):
        if task.topic not in {'arbitrage','market','macro','prediction','risk','alpha','research'}: return
        confidence=float(assessment.get('confidence',0.0)); evidence=int(assessment.get('evidence_count',0))
        edge=0.0
        text=' '.join(getattr(r,'snippet','') for r in results).lower()
        if task.topic == 'arbitrage' and any(x in text for x in ('arbitrage','spread','mispricing','price difference')):
            edge=0.005
        candidate=AlertCandidate(title=task.question[:120],category='arbitrage' if task.topic=='arbitrage' else task.topic,summary=f'{evidence} source-backed result(s) found for: {task.question}',confidence=confidence,edge=edge,sources=tuple(getattr(r,'url','') for r in results if getattr(r,'url',''))[:5],agent=task.requester)
        self.alert_candidates.append({**candidate.__dict__,'severity':candidate.severity})
        if self.alerts.send(candidate): self.stats.alerts_sent+=1

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
        return {'civilization':state,'research_runtime':{'coordinator':self.coordinator.snapshot(),'stats':self.stats.__dict__.copy(),'drained':len(drained),'queued_before_cycle':queued,'knowledge_graph':self.knowledge_graph.snapshot(),'quality':self.quality.snapshot(),'contradictions':self.contradictions.snapshot(),'failures':self.failures[-20:],'alerts':self.alert_candidates[-20:],'email':self.alerts.snapshot(),'you':self.researcher.snapshot()}}

    def snapshot(self):
        return {'coordinator':self.coordinator.snapshot(),'stats':self.stats.__dict__.copy(),'knowledge_graph':self.knowledge_graph.snapshot(),'quality':self.quality.snapshot(),'contradictions':self.contradictions.snapshot(),'failures':self.failures[-20:],'alerts':self.alert_candidates[-20:],'email':self.alerts.snapshot(),'you':self.researcher.snapshot(),'civilization':self.civilization.snapshot()}
