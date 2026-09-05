from __future__ import annotations
from dataclasses import dataclass, asdict
from random import Random
from time import time
from typing import Iterable

@dataclass
class StrategyMeme:
    meme_id:str; name:str; thesis:str; origin:str; generation:int; fitness:float=0.; carriers:int=1; mutations:int=0; support:int=0; challenges:int=0
@dataclass
class Organization:
    org_id:str; name:str; founder:str; mission:str; members:list[str]; treasury:float=0.; influence:float=0.

class EmergenceEngine:
    """Bounded social/economic emergence layer."""
    MISSIONS=('compound knowledge','protect capital','discover new markets','maximize evidence quality','build cooperative advantage')
    def __init__(self,seed=42,meme_limit=500,organization_limit=100,event_limit=250):
        self.rng=Random(seed); self.generation=0; self.meme_limit=max(50,meme_limit); self.organization_limit=max(20,organization_limit); self.event_limit=max(50,event_limit); self.memes={}; self.organizations={}; self.events=[]; self.discovery_points=0.; self.innovation_points=0.; self.social_capital=0.
    def seed_population(self,agents):
        for agent in agents:self._ensure_meme(agent.agent_id,agent.archetype,f'{agent.archetype} research doctrine')
    def _trim(self):
        if len(self.memes)>self.meme_limit:
            keep=sorted(self.memes.values(),key=lambda m:(m.fitness,m.carriers,m.generation),reverse=True)[:self.meme_limit]; self.memes={m.meme_id:m for m in keep}
        if len(self.organizations)>self.organization_limit:
            keep=sorted(self.organizations.values(),key=lambda o:(o.influence,o.treasury),reverse=True)[:self.organization_limit]; self.organizations={o.org_id:o for o in keep}
        self.events=self.events[-self.event_limit:]
    def _ensure_meme(self,agent_id,archetype,thesis):
        meme_id=f'M-{agent_id}-{archetype}'
        if meme_id not in self.memes:self.memes[meme_id]=StrategyMeme(meme_id,f'{archetype}-doctrine',str(thesis)[:800],agent_id,self.generation)
        return self.memes[meme_id]
    def observe(self,agent,idea,peers,tick):
        source=self._ensure_meme(agent.agent_id,agent.archetype,idea.thesis); source.fitness=max(source.fitness,float(idea.fitness)); self.discovery_points+=max(0.,idea.fitness)
        if peers and self.rng.random()<min(.95,.20+agent.cooperation*.55): source.carriers+=1; self.social_capital+=.25; self._record(tick,'idea_adopted',agent.agent_id,self.rng.choice(peers).agent_id,source.meme_id)
        if self.rng.random()<agent.curiosity*.30:
            mutation_id=f'MUT-{tick}-{agent.agent_id}-{self.rng.randrange(1_000_000)}'; self.memes[mutation_id]=StrategyMeme(mutation_id,f'mutation-{agent.archetype}',f'{idea.thesis} | mutation: stricter evidence threshold',agent.agent_id,self.generation+1,fitness=idea.fitness*.9,mutations=1); self.innovation_points+=1.; self._record(tick,'idea_mutated',agent.agent_id,None,mutation_id); self._trim()
    def form_organizations(self,agents,tick):
        agents=list(agents)
        if len(agents)<3:return
        leaders=sorted(agents,key=lambda a:a.reputation+a.cooperation+a.curiosity,reverse=True)[:5]
        for index,leader in enumerate(leaders):
            if len(self.organizations)>=self.organization_limit:break
            org_id=f'ORG-{self.generation:04d}-{index+1:02d}'
            if org_id in self.organizations:continue
            candidates=[a for a in agents if a.agent_id!=leader.agent_id and a.archetype!=leader.archetype]; members=[leader.agent_id]+[a.agent_id for a in self.rng.sample(candidates,min(4,len(candidates)))]; mission=self.rng.choice(self.MISSIONS); self.organizations[org_id]=Organization(org_id,f'{mission.title()} Guild',leader.agent_id,mission,members,100.+leader.reputation*50.,min(1.,.25+leader.cooperation*.5)); self._record(tick,'organization_formed',leader.agent_id,None,org_id)
    def economic_tick(self,agents,tick):
        agents=list(agents)
        for org in self.organizations.values():
            productivity=sum(next((a.intelligence.capability_score for a in agents if a.agent_id==m),0.) for m in org.members); org.treasury+=1.+productivity*.05; org.influence=min(1.,org.influence+.002*len(org.members))
        self.social_capital=min(1000.,self.social_capital+max(1,len(self.organizations))*.05); self.discovery_points*=.995; self.innovation_points*=.998
    def advance(self,agents,tick):self.form_organizations(agents,tick); self.economic_tick(agents,tick); self.generation+=1; self._trim()
    def _record(self,tick,event,actor,target,object_id):self.events.append({'tick':tick,'generation':self.generation,'event':event,'actor':actor,'target':target,'object':object_id,'at':time()})
    def snapshot(self):
        top=sorted(self.memes.values(),key=lambda x:(x.fitness,x.carriers,x.support-x.challenges),reverse=True)[:15]; return {'generation':self.generation,'memes':len(self.memes),'organizations':len(self.organizations),'discovery_points':round(self.discovery_points,3),'innovation_points':round(self.innovation_points,3),'social_capital':round(self.social_capital,3),'top_memes':[asdict(m) for m in top],'organizations_state':[asdict(o) for o in list(self.organizations.values())[:20]],'events':self.events[-30:]}
