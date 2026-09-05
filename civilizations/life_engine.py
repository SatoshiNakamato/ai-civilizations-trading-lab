from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Dict, List

@dataclass
class Memory:
    tick: int; kind: str; text: str; importance: float = 0.5

@dataclass
class Relationship:
    trust: float = 0.0; bond: float = 0.0; conflict: float = 0.0; interactions: int = 0

@dataclass
class LifeState:
    energy: float = 1.0; curiosity: float = 0.5; belonging: float = 0.5; security: float = 0.5; achievement: float = 0.5; wellbeing: float = 0.75

class LifeEngine:
    """Persistent individual-life model for AEON beings."""
    def __init__(self, seed: int = 42, memory_limit: int = 80):
        self.rng=Random(seed); self.memory_limit=memory_limit; self.memories:Dict[str,List[Memory]]={}; self.relationships={}; self.states={}; self.self_models={}; self.legacies={}

    def register(self, agent_id: str, values: List[str] | None = None) -> None:
        self.memories.setdefault(agent_id,[]); self.relationships.setdefault(agent_id,{}); self.states.setdefault(agent_id,LifeState()); self.self_models.setdefault(agent_id,{"identity":agent_id,"values":list(values or ["curiosity","survival","growth"]),"beliefs_changed":0,"reflections":0,"life_stage":"young","purpose":"discover and improve","individuality":self.rng.uniform(.25,.95)}); self.legacies.setdefault(agent_id,[])

    def inspect(self, agent_id: str) -> dict:
        self.register(agent_id)
        return {"id":agent_id,"state":vars(self.states[agent_id]).copy(),"self_model":dict(self.self_models[agent_id]),"memories":[vars(m).copy() for m in self.memories[agent_id]],"relationships":{k:vars(v).copy() for k,v in self.relationships[agent_id].items()},"legacy":list(self.legacies[agent_id])}

    def remember(self, agent_id,tick,text,kind="experience",importance=.5):
        self.register(agent_id); self.memories[agent_id].append(Memory(tick,kind,text[:500],max(0,min(1,importance)))); self.memories[agent_id]=sorted(self.memories[agent_id],key=lambda m:(m.importance,m.tick),reverse=True)[:self.memory_limit]

    def interact(self,a,b,tick,outcome):
        self.register(a); self.register(b)
        for left,right in ((a,b),(b,a)):
            rel=self.relationships[left].setdefault(right,Relationship()); rel.interactions+=1
            if outcome>=0: rel.trust=min(1,rel.trust+.03*outcome); rel.bond=min(1,rel.bond+.02*outcome)
            else: rel.conflict=min(1,rel.conflict+.04*abs(outcome))
            self.remember(left,tick,f"Interaction with {right}: outcome={outcome:.3f}","relationship",.45)

    def experience(self,agent_id,tick,success,novelty=.5):
        self.register(agent_id); s=self.states[agent_id]; s.energy=max(0,min(1,s.energy+.05*success-.03)); s.curiosity=max(0,min(1,s.curiosity+.04*novelty-.01*success)); s.achievement=max(0,min(1,s.achievement+.04*success)); s.wellbeing=max(0,min(1,.45*s.energy+.35*s.belonging+.20*s.achievement)); self.remember(agent_id,tick,f"Outcome={success:.3f}; novelty={novelty:.3f}","experience",min(1,.4+novelty*.4))

    def reflect(self,agent_id,tick):
        self.register(agent_id); memories=self.memories[agent_id][-8:]; reflection=("I have little history yet; I should explore before forming strong beliefs." if not memories else f"I have {len(memories)} recent experiences; I should adapt to what repeatedly worked and failed."); model=self.self_models[agent_id]; model["reflections"]=int(model["reflections"])+1
        if model["reflections"]>5:model["life_stage"]="established"
        self.remember(agent_id,tick,reflection,"reflection",.8); return reflection

    def teach(self,parent,child,tick):
        self.register(parent); self.register(child); lessons=[m.text for m in self.memories[parent] if m.kind in {"reflection","discovery"}][:5]
        for lesson in lessons:self.remember(child,tick,f"Inherited lesson from {parent}: {lesson}","inheritance",.6)
        self.legacies[parent].append(child); return lessons

    def snapshot(self,agent_ids=None):
        ids=agent_ids or list(self.states); return {"beings":len(ids),"memories":sum(len(self.memories.get(i,[])) for i in ids),"relationships":sum(len(self.relationships.get(i,{})) for i in ids),"reflections":sum(int(self.self_models.get(i,{}).get("reflections",0)) for i in ids),"life_stages":{s:sum(1 for i in ids if self.self_models.get(i,{}).get("life_stage")==s) for s in {"young","established"}}}
