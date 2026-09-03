from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from random import Random
from time import time
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from .core import Agent, Idea


@dataclass
class Evaluation:
    idea_id: str
    score: float
    evidence: str

@dataclass
class Prediction:
    agent_id: str
    asset: str
    hypothesis: str
    prediction: float
    confidence: float
    evidence: int
    created_at: float
    outcome: float | None = None
    correct: bool | None = None

@dataclass
class Knowledge:
    author: str
    topic: str
    claim: str
    evidence: list[str]
    challenges: int = 0
    support: int = 0
    created_at: float = 0.0

class CivilizationEvolution:
    """Persistent evidence-driven memory, specialization and generation scoring."""
    def __init__(self, path: str = "data/civilization_memory.json"):
        self.path = Path(path); self.generation = 0
        self.predictions: list[Prediction] = []; self.knowledge: list[Knowledge] = []
        self.specializations: dict[str, str] = {}; self._load()
    def _load(self):
        if not self.path.exists(): return
        try:
            d=json.loads(self.path.read_text()); self.generation=d.get("generation",0)
            self.predictions=[Prediction(**x) for x in d.get("predictions",[])]; self.knowledge=[Knowledge(**x) for x in d.get("knowledge",[])]
            self.specializations=d.get("specializations",{})
        except (OSError,ValueError,TypeError): pass
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True); tmp=self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps({'generation':self.generation,'predictions':[asdict(x) for x in self.predictions],'knowledge':[asdict(x) for x in self.knowledge],'specializations':self.specializations},indent=2)); tmp.replace(self.path)
    def record_prediction(self,agent_id,asset,hypothesis,prediction,confidence,evidence=0):
        p=Prediction(agent_id,asset,hypothesis,prediction,confidence,evidence,time()); self.predictions.append(p); self.save(); return p
    def resolve_prediction(self,index,outcome,tolerance=0.01):
        p=self.predictions[index]; p.outcome=outcome; p.correct=abs(p.prediction-outcome)<=tolerance; self.save(); return p
    def publish(self,author,topic,claim,evidence=()):
        k=Knowledge(author,topic,claim,list(evidence),created_at=time()); self.knowledge.append(k); self.save(); return k
    def challenge(self,index,supported):
        k=self.knowledge[index]; k.support += int(supported); k.challenges += int(not supported); self.save(); return k
    def score_agents(self):
        scores={}
        for p in self.predictions:
            if p.correct is None: continue
            r=scores.setdefault(p.agent_id,{'observations':0,'correct':0}); r['observations']+=1; r['correct']+=int(p.correct)
        for r in scores.values(): r['accuracy']=r['correct']/r['observations'] if r['observations'] else 0.0
        return dict(sorted(scores.items(),key=lambda kv:kv[1]['accuracy'],reverse=True))
    def specialize(self,agent_id,role):
        allowed={'arbitrage','onchain','macro','alpha','risk','validation','research','skeptic'}
        if role not in allowed: raise ValueError(f'unknown specialization: {role}')
        self.specializations[agent_id]=role; self.save()
    def evolve(self,agents=()):
        scores=self.score_agents(); self.generation+=1; roles=['arbitrage','onchain','macro','alpha','risk','validation','research','skeptic']
        ids=list(scores) or list(self.specializations) or [getattr(a,'agent_id',str(a)) for a in agents]
        for i,aid in enumerate(ids): self.specializations.setdefault(aid,roles[i%len(roles)])
        self.save(); return {'generation':self.generation,'scores':scores,'specializations':dict(self.specializations)}
    def snapshot(self):
        return {'generation':self.generation,'predictions':len(self.predictions),'knowledge':len(self.knowledge),'specializations':dict(self.specializations),'agent_scores':self.score_agents()}


def evaluate_idea(idea: "Idea", rng: Random) -> Evaluation:
    signal_quality=rng.uniform(0.0,1.0); robustness=rng.uniform(0.0,1.0); complexity_penalty=rng.uniform(0.0,0.25)
    return Evaluation(idea.title,max(0.0,min(1.0,0.55*signal_quality+0.45*robustness-complexity_penalty)),"simulated evidence")

def mutate(idea: "Idea", agent: "Agent", rng: Random) -> "Idea":
    from .core import Idea
    mutation=rng.choice(['tighten the risk filter','add a volatility regime filter','require independent confirmation','reduce exposure during drawdowns','test the signal at another horizon'])
    return Idea(title=f"{idea.title}|{mutation.replace(' ','_')}",thesis=f"{idea.thesis} Then {mutation}.",origin=agent.agent_id,generation=idea.generation+1,lineage=idea.lineage+[idea.origin])

def crossover(a: "Idea", b: "Idea", agent: "Agent", rng: Random) -> "Idea":
    from .core import Idea
    return Idea(title=f"cross({a.title[:24]}+{b.title[:24]})-{rng.randrange(1_000_000)}",thesis=f"Combine [{a.thesis}] with [{b.thesis}] and test the interaction out-of-sample.",origin=agent.agent_id,generation=max(a.generation,b.generation)+1,lineage=a.lineage+[a.origin,b.origin])

def rank_ideas(ideas: Iterable["Idea"]) -> list["Idea"]:
    return sorted(ideas,key=lambda x:x.fitness,reverse=True)
