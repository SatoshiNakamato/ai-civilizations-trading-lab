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
    def __init__(self, runtime, root="world_state", seed=42):
        self.runtime=runtime; self.life=runtime.life; self.world=runtime.world
        self.rng=Random(seed); self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.decisions=[]

    def step(self):
        self.runtime.civilization.step(); tick=self.runtime.civilization.tick
        ids=list(self.runtime.civilization.agents)
        for aid in ids:
            agent=self.runtime.civilization.agents[aid]
            self.life.experience(aid,tick,agent.intelligence.capability_score,agent.curiosity)
            if tick%5==0: self.life.reflect(aid,tick)
            result=self.life.evolve(aid,tick); action=result['action']; purpose=str(result['purpose'])
            reason=f"{action} selected from current needs, history and individuality"
            d=BeingDecision(aid,tick,action,purpose,reason); self.decisions.append(d)
            if self.rng.random()<0.35:
                kind=action.replace('socialize','social')
                path=self.world.create_artifact(aid,f"{aid}/life-{tick}-{kind}.md",f"# {kind}\nagent={aid}\ntick={tick}\npurpose={purpose}\n")
                self.life.remember(aid,tick,f"I chose {action} and created {path}.","agency",0.85)
        self.decisions=self.decisions[-300:]
        snapshot=self.life.snapshot(ids)
        snapshot.update({'tick':tick,'recent_decisions':[asdict(x) for x in self.decisions[-20:]],'internet':self.world.snapshot()})
        (self.root/'latest.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
        return snapshot

    def run(self,steps=1):
        result={}
        for _ in range(max(1,min(1000,steps))): result=self.step()
        return result
