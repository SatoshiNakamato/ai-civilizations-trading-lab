from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from random import Random
from .civilization_platform import CivilizationPlatform
from .memory_guard import collect, snapshot as memory_snapshot
from .endurance import EnduranceController
from .world_dynamics import WorldDynamics
from .notifications import NotificationGovernor, NotificationGovernorConfig, SMTPEmailSender
from .agent_communication import AgentCommunicationBus
from .learning_communication import CollectiveLearning
from .evolution_frontier import EvolutionFrontier
from .collective_evolution import CollectiveEvolutionLoop

@dataclass(slots=True)
class BeingDecision:
    agent:str; tick:int; action:str; purpose:str; reason:str

class AutonomousWorld:
    """Bounded-cost life loop with governed research, peer learning and alerts."""
    def __init__(self,runtime,root='world_state',seed=42):
        self.runtime=runtime; self.life=runtime.life; self.world=runtime.world; self.rng=Random(seed); self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True); self.decisions=[]; self.platform=CivilizationPlatform(root=root,seed=seed,active_budget=8); self.endurance=EnduranceController(); self.dynamics=WorldDynamics(self.platform,seed=seed); self.persist_every=5
        self.notifications=NotificationGovernor(SMTPEmailSender(), NotificationGovernorConfig.from_env())
        self.bus=AgentCommunicationBus()
        self.collective=CollectiveLearning(self.bus,seed=seed)
        self.frontier=EvolutionFrontier()
        self.collective_evolution=CollectiveEvolutionLoop(self.bus,self.collective,self.frontier,self.platform)
        for aid,agent in self.runtime.civilization.agents.items(): self.platform.register(aid,{'archetype':agent.archetype})
    def _evolve(self,aid):
        s=self.life.states[aid]; model=self.life.self_models[aid]; scores={'explore':s.curiosity,'build':s.achievement,'socialize':s.belonging,'protect':s.security,'reflect':.35}; individuality=float(model.get('individuality',.5)); scores={k:max(0.,v+self.rng.uniform(-.05,.05)*individuality) for k,v in scores.items()}; action=max(scores,key=scores.get); old=str(model.get('purpose','discover')); choices={'explore':['discover','understand','invent'],'build':['build','invent','compete'],'socialize':['connect','protect','build'],'reflect':['understand myself']}; purpose=self.rng.choice(choices[action]) if action in choices and scores[action]>.45 else old; model['purpose']=purpose; hist=model.setdefault('preferred_actions',[]); hist.append(action); model['preferred_actions']=hist[-20:]
        if purpose!=old:self.life.remember(aid,self.runtime.civilization.tick,f'My purpose changed from {old} to {purpose} after experience.','identity_change',.9)
        return action,purpose
    def _internet_learning(self,aid,purpose,tick):
        query=(purpose.replace('_',' ')+' research').strip()
        try:
            result=self.world.search(aid,query); results=(result.get('results') or [])[:3]
            if results:
                first=results[0]; self.life.remember(aid,tick,f"I searched for '{query}' and found {first.get('title','untitled')} — {first.get('url','')}",'web_learning',.75); self.life.states[aid].curiosity=min(1.,self.life.states[aid].curiosity+.03); self.platform.learn(aid,query,first.get('excerpt','')[:300],.7,tick); return {'query':query,'results':results}
        except Exception as exc:self.life.remember(aid,tick,f'Internet search failed: {type(exc).__name__}','web_failure',.2)
        return {'query':query,'results':[]}
    def notify_opportunity(self, *, severity: str, subject: str, body: str) -> dict:
        result=self.notifications.notify(severity=severity, subject=subject, body=body)
        return result
    def step(self):
        self.notifications.begin_cycle()
        ids=list(self.runtime.civilization.agents); tick_next=self.runtime.civilization.tick+1
        guard=self.endurance.check(tick_next,self.platform.active_budget); self.platform.active_budget=guard['active_budget']; active=self.platform.schedule(ids,tick_next); self.runtime.civilization.step(active_ids=active); tick=self.runtime.civilization.tick; web_learning=None
        evidence={}
        for aid in ids:
            model=self.life.self_models.get(aid,{})
            purpose=str(model.get('purpose','discover'))
            if aid in active:
                agent=self.runtime.civilization.agents[aid]; self.platform.choose_goal(aid); action,purpose=self._evolve(aid); outcome=max(0.,min(1.,agent.intelligence.capability_score/100.)); self.life.experience(aid,tick,outcome,.45)
                evidence[aid]=f'{aid} proposes {action} toward {purpose}; capability score={outcome:.3f}. Challenge assumptions and compare with peer evidence.'
                if action=='explore' and web_learning is None:web_learning=self._internet_learning(aid,purpose,tick)
                elif action=='build':self.platform.create(aid,'prototype',tick,f'purpose={purpose}')
                elif action=='socialize':
                    peers=[x for x in active if x!=aid]
                    if peers:self.platform.social(aid,self.rng.choice(peers),tick,True)
                elif action=='trade':
                    peers=[x for x in active if x!=aid]
                    if peers:self.platform.negotiate(aid,self.rng.choice(peers),tick)
                elif action=='experiment':self.platform.experiment(aid,purpose,tick)
                if self.rng.random()<.25:self.platform.employ(aid,action,purpose,tick)
                if self.rng.random()<.18:self.platform.organize(aid,tick)
                if tick%5==0:self.life.reflect(aid,tick)
                self.platform.evolve(aid,tick)
                self.decisions.append(BeingDecision(aid,tick,action,purpose,f'{action} selected from needs, memory, goals and individuality'))
            else:
                evidence[aid]=f'{aid} retained prior purpose={purpose}; waiting for active execution while contributing prior knowledge.'

        evolution=self.collective_evolution.run(ids,tick=tick,evidence=evidence,active_ids=active)
        diagnostics=self.frontier.diagnose(tick,active,evolution['research_exchanges'],evolution['debates'])
        dynamics=self.dynamics.tick(active,tick)
        self.platform.generation(tick)
        self.decisions=self.decisions[-100:]
        collect()
        guard=self.endurance.check(tick,self.platform.active_budget); self.platform.active_budget=guard['active_budget']
        should_persist=(tick == 1 or tick % self.persist_every == 0 or guard['level'] != 'normal')
        if should_persist:self.platform.save()
        snapshot=self.life.snapshot(ids); snapshot.update({'tick':tick,'recent_decisions':[asdict(x) for x in self.decisions[-20:]],'internet_learning':web_learning,'internet':self.world.snapshot(),'civilization':self.platform.snapshot(),'observatory':self.platform.observatory(),'dynamics':dynamics,'memory':memory_snapshot(),'endurance':guard,'notifications':self.notifications.snapshot(),'collective_learning':self.collective.snapshot(),'collective_exchange_count':evolution['research_exchanges'],'collective_debate_count':evolution['debates'],'collective_evolution':evolution,'collective_evolution_loop':self.collective_evolution.snapshot(),'evolution_frontier':self.frontier.command_snapshot(tick,diagnostics,self.collective.snapshot(),getattr(self.platform,'generation_count',None))})
        if should_persist:(self.root/'latest.json').write_text(json.dumps(snapshot,separators=(',',':'),default=str),encoding='utf-8')
        return snapshot
    def run(self,steps=1):
        result={}
        for _ in range(max(1,min(1000,steps))):result=self.step()
        if result and self.runtime.civilization.tick % self.persist_every != 0:
            self.platform.save(); (self.root/'latest.json').write_text(json.dumps(result,separators=(',',':'),default=str),encoding='utf-8')
        return result
