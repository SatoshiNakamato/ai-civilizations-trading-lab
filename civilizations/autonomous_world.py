from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from random import Random
from .civilization_platform import CivilizationPlatform

@dataclass
class BeingDecision:
    agent: str
    tick: int
    action: str
    purpose: str
    reason: str

class AutonomousWorld:
    """Canonical bounded-cost life loop for the AEON civilization."""
    def __init__(self, runtime, root='world_state', seed=42):
        self.runtime=runtime; self.life=runtime.life; self.world=runtime.world
        self.rng=Random(seed); self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.decisions=[]; self._cursor=0; self.platform=CivilizationPlatform(root=root,seed=seed,active_budget=8)
        for aid,agent in self.runtime.civilization.agents.items(): self.platform.register(aid,{'archetype':agent.archetype})

    def _evolve(self,aid):
        s=self.life.states[aid]; model=self.life.self_models[aid]
        scores={'explore':s.curiosity,'build':s.achievement,'socialize':s.belonging,'protect':s.security,'reflect':.35}
        for k in scores: scores[k]=max(0.0,scores[k]+self.rng.uniform(-.05,.05)*float(model.get('individuality',.5)))
        action=max(scores,key=scores.get); old=str(model.get('purpose','discover')); purpose=old
        choices={'explore':['discover','understand','invent'],'build':['build','invent','compete'],'socialize':['connect','protect','build'],'reflect':['understand myself']}
        if action in choices and scores[action]>.45: purpose=self.rng.choice(choices[action])
        model['purpose']=purpose; model.setdefault('preferred_actions',[]).append(action); model['preferred_actions']=model['preferred_actions'][-30:]
        if purpose!=old:self.life.remember(aid,self.runtime.civilization.tick,f'My purpose changed from {old} to {purpose} after experience.','identity_change',.9)
        return action,purpose

    def _internet_learning(self,aid,purpose,tick):
        query=(purpose.replace('_',' ')+' research').strip()
        try:
            result=self.world.search(aid,query)
            results=result.get('results') or []
            if results:
                first=results[0]; self.life.remember(aid,tick,f"I searched for '{query}' and found {first.get('title','untitled')} — {first.get('url','')}",'web_learning',.75); self.life.states[aid].curiosity=min(1.0,self.life.states[aid].curiosity+.03); self.platform.learn(aid,query,first.get('excerpt',''),.7,tick); return {'query':query,'results':results[:5]}
        except Exception as exc:
            self.life.remember(aid,tick,f'Internet search failed: {type(exc).__name__}','web_failure',.2)
        return {'query':query,'results':[]}

    def step(self):
        ids=list(self.runtime.civilization.agents)
        active=self.platform.schedule(ids,self.runtime.civilization.tick+1)
        # The trading core is intentionally stepped once, but expensive life actions
        # are budgeted to a small active cohort to keep Termux/Voroa memory and network use low.
        self.runtime.civilization.step(active_ids=active)
        tick=self.runtime.civilization.tick; web_learning=None
        for aid in active:
            agent=self.runtime.civilization.agents[aid]; goal=self.platform.choose_goal(aid); action,purpose=self._evolve(aid)
            outcome=max(0.0,min(1.0,agent.intelligence.capability_score/100.0)); self.life.experience(aid,tick,outcome,.45)
            if action=='explore' and self.life.states[aid].curiosity>=.2 and web_learning is None: web_learning=self._internet_learning(aid,purpose,tick)
            elif action=='build': self.platform.create(aid,'prototype',tick,f'purpose={purpose}')
            elif action=='experiment': self.platform.experiment(aid,purpose,tick)
            elif action=='connect':
                peers=[x for x in active if x!=aid]
                if peers:self.platform.social(aid,self.rng.choice(peers),tick,True)
            elif action=='trade':
                peers=[x for x in active if x!=aid]
                if peers:self.platform.negotiate(aid,self.rng.choice(peers),tick)
            if self.rng.random()<.25:self.platform.employ(aid,action,purpose,tick)
            if self.rng.random()<.18:self.platform.organize(aid,tick)
            if tick%5==0:self.life.reflect(aid,tick)
            self.platform.evolve(aid,tick)
            self.decisions.append(BeingDecision(aid,tick,action,purpose,f'{action} selected from needs, memory, goals and individuality'))
        self.platform.generation(tick); self.platform.save(); self.decisions=self.decisions[-200:]
        snapshot=self.life.snapshot(ids); snapshot.update({'tick':tick,'recent_decisions':[asdict(x) for x in self.decisions[-20:]],'internet_learning':web_learning,'internet':self.world.snapshot(),'civilization':self.platform.snapshot(),'observatory':self.platform.observatory()})
        (self.root/'latest.json').write_text(json.dumps(snapshot,indent=2,default=str),encoding='utf-8'); return snapshot

    def run(self,steps=1):
        result={}
        for _ in range(max(1,min(1000,steps))): result=self.step()
        return result
