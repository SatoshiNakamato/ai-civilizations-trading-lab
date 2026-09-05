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
    """Persistent life loop: perceive, choose, learn, create and evolve."""
    def __init__(self, runtime, root='world_state', seed=42):
        self.runtime=runtime; self.life=runtime.life; self.world=runtime.world
        self.rng=Random(seed); self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True); self.decisions=[]

    def _evolve(self,aid):
        s=self.life.states[aid]; model=self.life.self_models[aid]
        scores={'explore':s.curiosity,'build':s.achievement,'socialize':s.belonging,'protect':s.security,'reflect':0.35}
        for k in scores: scores[k]=max(0.0,scores[k]+self.rng.uniform(-.08,.08)*float(model.get('individuality',.5)))
        action=max(scores,key=scores.get); old=str(model.get('purpose','discover'))
        purpose=old
        if action=='explore' and s.curiosity>.7: purpose=self.rng.choice(['discover','understand','invent'])
        elif action=='build' and s.achievement>.7: purpose=self.rng.choice(['build','invent','compete'])
        elif action=='socialize' and s.belonging>.7: purpose=self.rng.choice(['connect','protect','build'])
        model['purpose']=purpose; model.setdefault('preferred_actions',[]).append(action); model['preferred_actions']=model['preferred_actions'][-30:]
        if purpose!=old: self.life.remember(aid,self.runtime.civilization.tick,f'My purpose changed from {old} to {purpose} after experience.','identity_change',.9)
        return action,purpose

    def step(self):
        self.runtime.civilization.step(); tick=self.runtime.civilization.tick; ids=list(self.runtime.civilization.agents)
        for aid in ids:
            agent=self.runtime.civilization.agents[aid]
            self.life.experience(aid,tick,agent.intelligence.capability_score,agent.curiosity)
            if tick%5==0: self.life.reflect(aid,tick)
            action,purpose=self._evolve(aid)
            self.decisions.append(BeingDecision(aid,tick,action,purpose,f'{action} selected from current needs, history and individuality'))
            if self.rng.random()<.35:
                kind=action.replace('socialize','social')
                path=self.world.create_artifact(aid,f'{aid}/life-{tick}-{kind}.md',f'# {kind}\nagent={aid}\ntick={tick}\npurpose={purpose}\n')
                self.life.remember(aid,tick,f'I chose {action} and created {path}.','agency',.85)
        self.decisions=self.decisions[-300:]
        snapshot=self.life.snapshot(ids); snapshot.update({'tick':tick,'recent_decisions':[asdict(x) for x in self.decisions[-20:]],'internet':self.world.snapshot()})
        (self.root/'latest.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8'); return snapshot

    def run(self,steps=1):
        result={}
        for _ in range(max(1,min(1000,steps))): result=self.step()
        return result
