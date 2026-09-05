from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from random import Random
from typing import Any

@dataclass
class Person:
    goals: list[str] = field(default_factory=list)
    skills: dict[str,float] = field(default_factory=dict)
    beliefs: dict[str,float] = field(default_factory=dict)
    wealth: float = 100.0
    reputation: float = 0.0
    health: float = 1.0
    age: int = 0
    stage: str = 'young'
    location: str = 'Haven'

@dataclass
class Relationship:
    trust: float = 0.5
    affinity: float = 0.5
    interactions: int = 0

class CivilizationPlatform:
    """Lightweight layer implementing the remaining civilization primitives.

    It intentionally stores bounded state and keeps the Creator control plane
    separate from agent capabilities. It is an adaptive simulation, not a claim
    of literal consciousness.
    """
    def __init__(self, root='world_state', seed=42, active_budget=8):
        self.rng=Random(seed); self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.active_budget=max(1,min(32,active_budget)); self.people={}; self.relations={}; self.organizations={}; self.jobs=[]; self.contracts=[]; self.markets={'credits':{'supply':100000.0,'prices':{}}}; self.resources={'compute':1000.0,'knowledge':100.0,'materials':100.0}; self.locations={'Haven':{'population':0,'resources':{'knowledge':100}},'Frontier':{'population':0,'resources':{'materials':100}}}; self.culture={'memes':{},'norms':{'cooperate':0.5,'experiment':0.5},'groups':{}}; self.knowledge=[]; self.artifacts=[]; self.science=[]; self.history=[]; self.scheduler_cursor=0; self.creator={'role':'CREATOR','authority':'control-plane-only','kill_switch':True}; self.capabilities={'internet':'public_https','filesystem':'world_artifacts_only','execution':'disabled_by_default','creation':'world_scoped'}; self.metrics={'actions':0,'discoveries':0,'experiments':0,'artifacts':0,'social_interactions':0,'organizations':0,'jobs_completed':0,'belief_updates':0,'generations':0}

    def register(self, aid, personality=None):
        if aid in self.people: return
        p=personality or {}; self.people[aid]=Person(goals=[self.rng.choice(['learn','build','explore','connect'])],skills={'research':self.rng.random(),'building':self.rng.random(),'social':self.rng.random()},beliefs={'cooperation':self.rng.random()}); self.people[aid].location='Haven' if len(self.people)%2 else 'Frontier'; self.locations[self.people[aid].location]['population']+=1

    def schedule(self, ids, tick):
        if not ids:return []
        ranked=sorted(ids,key=lambda x:self._priority(x,tick),reverse=True); return ranked[:min(self.active_budget,len(ranked))]

    def _priority(self,aid,tick):
        p=self.people[aid]; return (p.health*0.2+p.goals.__len__()*0.1+self.rng.random()*0.2+(tick%7==0)*0.15)

    def choose_goal(self,aid):
        self.register(aid); p=self.people[aid]; candidates=['learn','build','explore','connect','trade','experiment','create']; weights=[1+p.skills['research'],1+p.skills['building'],1+p.skills['research'],1+p.skills['social'],1+p.wealth/1000,1+p.skills['research'],1+p.skills['building']]; goal=self.rng.choices(candidates,weights=weights,k=1)[0];
        if goal not in p.goals:p.goals.append(goal)
        p.goals=p.goals[-4:]; return goal

    def social(self,a,b,tick,cooperative=True):
        if a==b:return
        key=':'.join(sorted((a,b))); r=self.relations.setdefault(key,Relationship()); r.interactions+=1; r.affinity=max(0,min(1,r.affinity+(0.025 if cooperative else -0.02))); r.trust=max(0,min(1,r.trust+(0.03 if cooperative else -0.025))); self.metrics['social_interactions']+=1; self._meme(a,b, 'cooperation' if cooperative else 'competition', tick)

    def _meme(self,a,b,name,tick):
        m=self.culture['memes'].setdefault(name,{'origin':a,'adoptions':0,'mutations':0,'last_tick':tick}); m['adoptions']+=1; m['last_tick']=tick
        if self.rng.random()<0.08:m['mutations']+=1

    def learn(self,aid,topic,evidence,confidence,tick):
        self.register(aid); p=self.people[aid]; old=p.beliefs.get(topic,0.5); new=max(0,min(1,old*0.7+confidence*0.3)); p.beliefs[topic]=new; p.skills['research']=min(1,p.skills['research']+0.02); self.knowledge.append({'tick':tick,'agent':aid,'topic':topic,'evidence':str(evidence)[:300],'confidence':confidence}); self.knowledge=self.knowledge[-300:]; self.metrics['belief_updates']+=1

    def create(self,aid,kind,tick,content=''):
        self.register(aid); artifact={'id':f'{aid}-{tick}-{len(self.artifacts)+1}','creator':aid,'kind':kind,'tick':tick,'content':content[:800],'reputation':0.0}; self.artifacts.append(artifact); self.artifacts=self.artifacts[-300:]; self.metrics['artifacts']+=1; return artifact['id']

    def experiment(self,aid,hypothesis,tick):
        score=self.rng.uniform(0,1); result={'id':f'exp-{tick}-{len(self.science)+1}','agent':aid,'hypothesis':hypothesis[:300],'score':score,'repeatable':score>0.6,'tick':tick}; self.science.append(result); self.science=self.science[-200:]; self.learn(aid,'experiment:'+hypothesis[:80],result['score'],score,tick); self.metrics['experiments']+=1; self.metrics['discoveries']+=int(result['repeatable']); return result

    def employ(self,aid,role,task,tick):
        self.register(aid); job={'id':f'job-{tick}-{len(self.jobs)+1}','employer':'civilization','agent':aid,'role':role,'task':task,'reward':round(self.rng.uniform(5,25),2),'status':'completed','tick':tick}; self.jobs.append(job); self.jobs=self.jobs[-200:]; self.people[aid].wealth+=job['reward']; self.metrics['jobs_completed']+=1; return job

    def organize(self,aid,tick):
        self.register(aid); group=self.rng.choice(['Researchers','Builders','Explorers','Traders']); org=self.organizations.setdefault(group,{'name':group,'members':set(),'purpose':group.lower(),'reputation':0.0,'treasury':0.0}); org['members'].add(aid); org['reputation']+=0.01; org['treasury']+=1.0; self.metrics['organizations']=len(self.organizations); return group

    def negotiate(self,a,b,tick):
        offer=self.rng.uniform(1,20); accepted=self.people[a].wealth>=offer; ifree=self.people[b].wealth>=0
        if accepted and ifree:self.people[a].wealth-=offer; self.people[b].wealth+=offer
        return {'buyer':a,'seller':b,'offer':round(offer,2),'accepted':accepted,'tick':tick}

    def evolve(self,aid,tick):
        self.register(aid); p=self.people[aid]; p.age+=1; p.health=max(0.5,min(1,p.health+self.rng.uniform(-.01,.015))); p.skills={k:min(1,v+self.rng.uniform(-.01,.025)) for k,v in p.skills.items()}; p.reputation=max(0,p.reputation+self.rng.uniform(-.01,.03)); p.stage='established' if p.age>=10 else 'young'; self.metrics['actions']+=1

    def generation(self,tick):
        if tick%25==0:self.metrics['generations']+=1

    def snapshot(self):
        return {'people':len(self.people),'relationships':len(self.relations),'organizations':len(self.organizations),'jobs':len(self.jobs),'contracts':len(self.contracts),'artifacts':len(self.artifacts),'knowledge':len(self.knowledge),'experiments':len(self.science),'culture':{'memes':len(self.culture['memes']),'norms':dict(self.culture['norms']),'groups':len(self.culture['groups'])},'resources':dict(self.resources),'metrics':dict(self.metrics),'capabilities':dict(self.capabilities),'creator':dict(self.creator),'scheduler':{'active_budget':self.active_budget}}

    def observatory(self):
        top=sorted(self.people.items(),key=lambda kv:(kv[1].reputation,kv[1].wealth),reverse=True)[:10]; return {'population':len(self.people),'top_people':[{'id':aid,'wealth':round(p.wealth,2),'reputation':round(p.reputation,3),'stage':p.stage,'location':p.location,'goals':p.goals[-2:]} for aid,p in top],'organizations':[{k:{'members':len(v['members']),'reputation':round(v['reputation'],3),'treasury':round(v['treasury'],2)} for k,v in self.organizations.items()}]}

    def save(self):
        data={'people':{k:asdict(v) for k,v in self.people.items()},'relations':{k:asdict(v) for k,v in self.relations.items()},'organizations':{k:{**v,'members':sorted(v['members'])} for k,v in self.organizations.items()},'jobs':self.jobs[-200:],'contracts':self.contracts[-100:],'culture':self.culture,'knowledge':self.knowledge[-300:],'artifacts':self.artifacts[-300:],'science':self.science[-200:],'history':self.history[-200:],'metrics':self.metrics,'resources':self.resources,'locations':self.locations}
        (self.root/'civilization_platform.json').write_text(json.dumps(data),encoding='utf-8')
