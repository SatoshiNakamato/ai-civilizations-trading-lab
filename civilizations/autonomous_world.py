from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from random import Random

@dataclass
class BeingDecision:
    agent: str
    tick: int
    action: str
    purpose: str
    reason: str

class AutonomousWorld:
    """One canonical life loop: perceive, choose, learn, create and evolve."""
    def __init__(self, runtime, root='world_state', seed=42):
        self.runtime=runtime; self.life=runtime.life; self.world=runtime.world
        self.rng=Random(seed); self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.decisions=[]; self._cursor=0

    def _evolve(self,aid):
        s=self.life.states[aid]; model=self.life.self_models[aid]
        scores={'explore':s.curiosity,'build':s.achievement,'socialize':s.belonging,'protect':s.security,'reflect':0.35}
        for k in scores: scores[k]=max(0.0,scores[k]+self.rng.uniform(-.08,.08)*float(model.get('individuality',.5)))
        action=max(scores,key=scores.get); old=str(model.get('purpose','discover'))
        purpose=old
        if action=='explore' and s.curiosity>.7: purpose=self.rng.choice(['discover','understand','invent'])
        elif action=='build' and s.achievement>.7: purpose=self.rng.choice(['build','invent','compete'])
        elif action=='socialize' and s.belonging>.7: purpose=self.rng.choice(['connect','protect','build'])
        elif action=='reflect': purpose='understand myself'
        model['purpose']=purpose; model.setdefault('preferred_actions',[]).append(action); model['preferred_actions']=model['preferred_actions'][-30:]
        if purpose!=old: self.life.remember(aid,self.runtime.civilization.tick,f'My purpose changed from {old} to {purpose} after experience.','identity_change',.9)
        return action,purpose

    def _internet_learning(self,aid,purpose,tick):
        """Give one curious being per tick a real public-web research opportunity."""
        query=(purpose.replace('_',' ') + ' research').strip()
        try:
            result=self.world.search(aid,query)
            if result.get('results'):
                first=result['results'][0]
                self.life.remember(aid,tick,f"I searched the public Internet for '{query}' and found: {first.get('title','untitled')} — {first.get('url','')}",'web_learning',.75)
                self.life.states[aid].curiosity=min(1.0,self.life.states[aid].curiosity+.03)
                return {'query':query,'results':result['results'][:5]}
        except Exception as exc:
            self.life.remember(aid,tick,f"My Internet search failed: {type(exc).__name__}",'web_failure',.2)
        return {'query':query,'results':[]}

    def step(self):
        self.runtime.civilization.step(); tick=self.runtime.civilization.tick; ids=list(self.runtime.civilization.agents)
        web_learning=None
        # Avoid 100 network calls per tick: one being gets a genuine research turn.
        if ids:
            aid=ids[self._cursor % len(ids)]; self._cursor+=1
            if self.life.states[aid].curiosity >= .2:
                web_learning=self._internet_learning(aid,self.life.self_models[aid].get('purpose','discover'),tick)
        for aid in ids:
            agent=self.runtime.civilization.agents[aid]
            self.life.experience(aid,tick,agent.intelligence.capability_score,agent.curiosity)
            if tick%5==0: self.life.reflect(aid,tick)
            action,purpose=self._evolve(aid)
            self.decisions.append(BeingDecision(aid,tick,action,purpose,f'{action} selected from current needs, history and individuality'))
            if self.rng.random()<.12:
                kind=action.replace('socialize','social')
                path=self.world.create_artifact(aid,f'{aid}/life-{tick}-{kind}.md',f'# {kind}\nagent={aid}\ntick={tick}\npurpose={purpose}\n')
                self.life.remember(aid,tick,f'I chose {action} and created {path}.','agency',.85)
        self.decisions=self.decisions[-200:]
        snapshot=self.life.snapshot(ids); snapshot.update({'tick':tick,'recent_decisions':[asdict(x) for x in self.decisions[-20:]],'internet_learning':web_learning,'internet':self.world.snapshot()})
        (self.root/'latest.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8'); return snapshot

    def run(self,steps=1):
        result={}
        for _ in range(max(1,min(1000,steps))): result=self.step()
        return result
