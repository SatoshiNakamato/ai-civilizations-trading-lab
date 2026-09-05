from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Iterable
if TYPE_CHECKING:
    from .core import Agent, Idea

@dataclass
class Evaluation:
    idea_id:str; score:float; evidence:str
@dataclass
class Prediction:
    agent_id:str; asset:str; hypothesis:str; prediction:float; confidence:float; evidence:int; created_at:float; interval:str='4h'; outcome:float|None=None; correct:bool|None=None; resolved_at:float|None=None; validation_passed:bool|None=None
@dataclass
class Knowledge:
    author:str; topic:str; claim:str; evidence:list[str]; challenges:int=0; support:int=0; created_at:float=0.0

class CivilizationEvolution:
    """Evidence-driven memory with strict retention limits for mobile runtimes."""
    def __init__(self,path='data/civilization_memory.json',prediction_limit=1000,knowledge_limit=500):
        self.path=Path(path); self.generation=0; self.prediction_limit=max(100,prediction_limit); self.knowledge_limit=max(100,knowledge_limit); self.predictions=[]; self.knowledge=[]; self.specializations={}; self._load()
    def _load(self):
        if not self.path.exists():return
        try:
            d=json.loads(self.path.read_text()); self.generation=d.get('generation',0); self.predictions=[Prediction(**x) for x in d.get('predictions',[])[-self.prediction_limit:]]; self.knowledge=[Knowledge(**x) for x in d.get('knowledge',[])[-self.knowledge_limit:]]; self.specializations=d.get('specializations',{})
        except (OSError,ValueError,TypeError):pass
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True); payload=json.dumps({'generation':self.generation,'predictions':[asdict(x) for x in self.predictions[-self.prediction_limit:]],'knowledge':[asdict(x) for x in self.knowledge[-self.knowledge_limit:]],'specializations':self.specializations},separators=(',',':')); tmp=self.path.with_name(self.path.name+'.tmp'); tmp.write_text(payload); tmp.replace(self.path)
    def record_prediction(self,agent_id,asset,hypothesis,prediction,confidence,evidence=0,interval='4h'):
        p=Prediction(agent_id,asset,hypothesis[:500],prediction,confidence,evidence,time(),interval=interval); self.predictions.append(p); self.predictions=self.predictions[-self.prediction_limit:]; self.save(); return p
    def resolve_prediction(self,index,outcome,tolerance=.01,validation_passed=None):
        p=self.predictions[index]; p.outcome=float(outcome); p.correct=abs(p.prediction-p.outcome)<=tolerance; p.validation_passed=validation_passed; p.resolved_at=time(); self.save(); return p
    def resolve_real_validation(self,results,min_samples=200,tolerance=.02):
        resolved=0
        for i,p in enumerate(self.predictions):
            if p.outcome is not None:continue
            result=results.get((p.asset,p.interval))
            if result is None or getattr(result,'samples',0)<min_samples:continue
            self.resolve_prediction(i,getattr(result,'score',0.0),tolerance,getattr(result,'passed',False)); resolved+=1
        return resolved
    def publish(self,author,topic,claim,evidence=()):
        k=Knowledge(author,topic,claim[:1000],list(evidence)[:5],created_at=time()); self.knowledge.append(k); self.knowledge=self.knowledge[-self.knowledge_limit:]; self.save(); return k
    def challenge(self,index,supported): k=self.knowledge[index]; k.support+=int(supported); k.challenges+=int(not supported); self.save(); return k
    def score_agents(self):
        scores={}
        for p in self.predictions:
            r=scores.setdefault(p.agent_id,{'observations':0,'resolved':0,'correct':0,'confidence_sum':0.0,'validation_passes':0,'validation_failures':0}); r['observations']+=1; r['confidence_sum']+=p.confidence
            if p.outcome is not None:r['resolved']+=1; r['correct']+=int(bool(p.correct)); r['validation_passes']+=int(p.validation_passed is True); r['validation_failures']+=int(p.validation_passed is False)
        for r in scores.values():r['accuracy']=r['correct']/r['resolved'] if r['resolved'] else 0.; r['resolution_rate']=r['resolved']/r['observations'] if r['observations'] else 0.; r['validation_pass_rate']=r['validation_passes']/r['resolved'] if r['resolved'] else 0.; r['avg_confidence']=r['confidence_sum']/r['observations'] if r['observations'] else 0.; r['leaderboard_score']=.7*r['accuracy']+.2*r['validation_pass_rate']+.1*r['resolution_rate']
        return dict(sorted(scores.items(),key=lambda kv:(kv[1]['leaderboard_score'],kv[1]['accuracy']),reverse=True))
    def leaderboard(self,limit=20):return [{'rank':i+1,'agent_id':aid,**stats} for i,(aid,stats) in enumerate(list(self.score_agents().items())[:limit])]
    def specialize(self,agent_id,role):
        if role not in {'arbitrage','onchain','macro','alpha','risk','validation','research','skeptic'}:raise ValueError(f'unknown specialization: {role}')
        self.specializations[agent_id]=role; self.save()
    def evolve(self,agents=()):
        scores=self.score_agents(); self.generation+=1; roles=['arbitrage','onchain','macro','alpha','risk','validation','research','skeptic']; ids=list(scores) or list(self.specializations) or [getattr(a,'agent_id',str(a)) for a in agents]
        for i,aid in enumerate(ids):self.specializations.setdefault(aid,roles[i%len(roles)])
        self.save(); return {'generation':self.generation,'scores':scores,'leaderboard':self.leaderboard(),'specializations':dict(self.specializations)}
    def snapshot(self):return {'generation':self.generation,'predictions':len(self.predictions),'resolved_predictions':sum(p.outcome is not None for p in self.predictions),'knowledge':len(self.knowledge),'specializations':dict(self.specializations),'agent_scores':self.score_agents(),'leaderboard':self.leaderboard()}

def mutate(idea:'Idea',agent:'Agent',rng)->'Idea':
    from .core import Idea
    mutation=rng.choice(['tighten the risk filter','add a volatility regime filter','require independent confirmation','reduce exposure during drawdowns','test the signal at another horizon']); return Idea(title=f'{idea.title}|{mutation.replace(" ","_")}',thesis=f'{idea.thesis} Then {mutation}.',origin=agent.agent_id,generation=idea.generation+1,lineage=idea.lineage+[idea.origin])
def crossover(a:'Idea',b:'Idea',agent:'Agent',rng)->'Idea':
    from .core import Idea
    return Idea(title=f'cross({a.title[:24]}+{b.title[:24]})-{rng.randrange(1_000_000)}',thesis=f'Combine [{a.thesis}] with [{b.thesis}] and test the interaction out-of-sample.',origin=agent.agent_id,generation=max(a.generation,b.generation)+1,lineage=a.lineage+[a.origin,b.origin])
def rank_ideas(ideas:Iterable['Idea'])->list['Idea']:return sorted(ideas,key=lambda x:(x.validation_passed,x.fitness),reverse=True)
