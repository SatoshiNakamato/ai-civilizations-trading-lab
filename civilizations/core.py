from __future__ import annotations
from dataclasses import dataclass, field
from random import Random
from typing import Dict, List
from .arena import CivilizationArena
from .communication import CommunicationNetwork
from .evolution import rank_ideas, CivilizationEvolution
from .emergence import EmergenceEngine
from .learning import Intelligence
from .research import PublicWebCollector, ResearchDesk
from .research_bridge import ResearchBridge
from .research_bureau import ResearchBureau
from .society import Society
from markets.verification import AlphaVerifier

ARCHETYPES=[('quant','Quant Researcher'),('arb','Arbitrage Hunter'),('macro','Macro Analyst'),('momentum','Momentum Trader'),('value','Value Researcher'),('contrarian','Contrarian'),('risk','Risk Manager'),('probability','Prediction-Market Analyst'),('microstructure','Market Microstructure Specialist'),('explorer','Strategy Explorer')]
@dataclass
class Idea:
    title:str; thesis:str; origin:str; fitness:float=0.0; generation:int=0; lineage:List[str]=field(default_factory=list); validation_score:float=0.0; validation_return:float=0.0; validation_drawdown:float=0.0; validation_samples:int=0; validation_passed:bool=False; validation_source:str=''
@dataclass
class Agent:
    agent_id:str; name:str; archetype:str; sex:str; risk_tolerance:float; curiosity:float; cooperation:float; intelligence:Intelligence=field(default_factory=Intelligence); ideas:List[Idea]=field(default_factory=list); wealth_score:float=0.0; reputation:float=0.0; age:int=0; beliefs:Dict[str,float]=field(default_factory=dict)
    def observe_and_propose(self,tick,rng,research_context=None):
        themes={'quant':'Test a statistical relationship and demand out-of-sample confirmation.','arb':'Search for temporary cross-market price discrepancies after fees, slippage and latency.','macro':'Map macroeconomic regime changes to asset behavior.','momentum':'Test price persistence while accounting for liquidity and transaction costs.','value':'Compare market price with a conservative fair-value estimate.','contrarian':'Look for crowded positioning and asymmetric reversal setups.','risk':'Improve position sizing using volatility, correlation and drawdown information.','probability':'Compare implied event probabilities with calibrated forecast probabilities.','microstructure':'Study spreads, liquidity and order-flow dynamics.','explorer':'Combine two unrelated signals into a falsifiable hypothesis.'}; base=themes[self.archetype]
        if research_context and research_context.get('sources'): base+=f" Evidence reviewed: {research_context['sources'][0]['excerpt'][:240]}"
        return Idea(f'{self.archetype}-idea-{tick}-{rng.randrange(1_000_000)}',base,self.agent_id,generation=tick)
    def evaluate(self,idea,validation):
        idea.validation_score=validation.score; idea.validation_return=validation.total_return; idea.validation_drawdown=validation.max_drawdown; idea.validation_samples=validation.samples; idea.validation_passed=validation.passed; idea.validation_source='real market candles / walk-forward verification'; idea.fitness=max(0,min(1,.5+validation.score)); self.intelligence.learn_from_research(validation.score,min(1,validation.samples/500),min(1,.25+self.intelligence.creativity/500)); return idea.fitness

class Civilization:
    def __init__(self,size=100,seed=42,civilization_id='CIV-001',arena=None):
        self.civilization_id=civilization_id; self.rng=Random(seed); self.tick=0; self.generation=0; self.max_ideas=500; self.max_agent_ideas=20; self.agents={}; self.global_ideas=[]; self.events=[]; self.network=CommunicationNetwork(); self.society=Society(); self.emergence=EmergenceEngine(seed); self.research=ResearchDesk(web_collector=PublicWebCollector()); self.research_bridge=ResearchBridge(self.research,self.research.web_collector); self.bureau=ResearchBureau(self.research.web_collector); self.evolution=CivilizationEvolution(); self.verifier=AlphaVerifier(); self.arena=arena or CivilizationArena(); self._validation_cache={}; self._seed_research(); self._create_population(size); self.emergence.seed_population(self.agents.values()); [self.evolution.specialize(a.agent_id,self._evolution_role(a.archetype)) for a in self.agents.values()]
    def _evolution_role(self,a): return {'arb':'arbitrage','quant':'alpha','macro':'macro','momentum':'alpha','value':'alpha','contrarian':'skeptic','risk':'risk','probability':'validation','microstructure':'arbitrage','explorer':'research'}.get(a,'research')
    def _seed_research(self): self.research.ingest('internal://protocol','Research protocol','Hypotheses must be falsifiable. Historical success does not guarantee future returns.')
    def _create_population(self,size):
        for i in range(size):
            key,role=ARCHETYPES[i%len(ARCHETYPES)]; self.agents[f'A{i+1:03d}']=Agent(f'A{i+1:03d}',f'{role} {i+1:03d}',key,'female' if i%2 else 'male',self.rng.random(),self.rng.random(),self.rng.random())
    def _research_query(self,a): return {'quant':'statistical out-of-sample','arb':'price discrepancy transaction costs','macro':'macro economic regime','momentum':'price persistence liquidity','value':'fair value valuation','contrarian':'crowded positioning reversal','risk':'volatility correlation drawdown','probability':'probability forecast calibration','microstructure':'market liquidity spread order flow','explorer':'falsifiable hypothesis validation'}[a.archetype]
    def _market_test(self,a):
        symbol={'arb':'BTCUSDT','quant':'BTCUSDT','macro':'ETHUSDT','momentum':'SOLUSDT','value':'ETHUSDT','contrarian':'SOLUSDT','risk':'BTCUSDT','probability':'ETHUSDT','microstructure':'BTCUSDT','explorer':'SOLUSDT'}[a.archetype]; interval={'macro':'4h','momentum':'1h','contrarian':'15m'}.get(a.archetype,'4h'); key=(symbol,interval)
        if key not in self._validation_cache:self._validation_cache[key]=self.verifier.verify(symbol,interval,500)
        return self._validation_cache[key]
    def _forecast_probability(self,agent,idea,validation):
        # Forecasts are explicit probabilistic claims, not disguised validation scores.
        # The current research signal is only a prior; the outcome must be resolved externally.
        base=.5 + (validation.score * .25) + ((agent.curiosity-.5) * .1)
        return max(.01,min(.99,base))
    def step(self,active_ids=None):
        self.tick+=1; self._validation_cache.clear(); proposals=[]; active=set(active_ids) if active_ids is not None else set(self.agents)
        for agent in (a for aid,a in self.agents.items() if aid in active):
            query=self._research_query(agent); self.bureau.submit_question(agent.agent_id,query,agent.curiosity); context=self.research_bridge.build_context(agent.agent_id,query,limit=3); idea=agent.observe_and_propose(self.tick,self.rng,context); validation=self._market_test(agent); agent.evaluate(idea,validation); agent.ideas.append(idea); agent.ideas=agent.ideas[-self.max_agent_ideas:]; self.global_ideas.append(idea); self.global_ideas=self.global_ideas[-self.max_ideas:]; probability=self._forecast_probability(agent,idea,validation); commitment=self.arena.commit(self.civilization_id,agent.agent_id,{'arb':'BTCUSDT','quant':'BTCUSDT','macro':'ETHUSDT','momentum':'SOLUSDT','value':'ETHUSDT','contrarian':'SOLUSDT','risk':'BTCUSDT','probability':'ETHUSDT','microstructure':'BTCUSDT','explorer':'SOLUSDT'}[agent.archetype],{'macro':'4h','momentum':'1h','contrarian':'15m'}.get(agent.archetype,'4h'),probability); self.arena.submit(commitment); self.evolution.record_prediction(agent.agent_id,'BTCUSDT',idea.thesis,validation.score,probability,validation.samples,'4h'); self.society.record_knowledge(f'{agent.archetype}:{idea.title}',idea.thesis,agent.agent_id,idea.fitness,self.generation); self.evolution.publish(agent.agent_id,agent.archetype,idea.thesis,[s.get('url','') for s in context.get('sources',[])]); self.emergence.observe(agent,idea,self._sample_peers(agent.agent_id,3),self.tick); proposals.append(idea)
        resolved=self.evolution.resolve_real_validation(self._validation_cache,min_samples=200,tolerance=.02); champions=rank_ideas(proposals)[:20]
        for idea in champions:
            for peer in self._sample_peers(idea.origin,3):
                sender=self.agents[idea.origin]; kind='endorse' if peer.cooperation>=.5 else 'challenge'; self.network.send(sender.agent_id,peer.agent_id,kind,f'{kind}: {idea.title}; real_score={idea.validation_score:.4f}; passed={idea.validation_passed}',self.tick); self.society.talk(self.generation,sender.agent_id,peer.agent_id,idea.title,'collaboration',.8); sender.intelligence.learn_from_collaboration(.8); self.network.update_reputation(sender.agent_id,.01 if idea.validation_passed else -.005)
        self.emergence.advance(self.agents.values(),self.tick); self.generation+=1; self.bureau.generation=self.generation; self.evolution.evolve(self.agents.values()); self.events.append(f'tick={self.tick}: active={len(active)}; emergence cycle complete; resolved={resolved}; arena_forecasts={len(self.arena.commitments)}; arena_resolved={len(self.arena.outcomes)}; organizations={len(self.emergence.organizations)}; memes={len(self.emergence.memes)}'); self.events=self.events[-100:]; return self.snapshot()
    def _sample_peers(self,origin,count): pool=[a for aid,a in self.agents.items() if aid!=origin]; self.rng.shuffle(pool); return pool[:count]
    def snapshot(self):
        top=sorted(self.global_ideas,key=lambda x:(x.validation_passed,x.fitness),reverse=True)[:10]; best=sorted(self.agents.values(),key=lambda a:a.intelligence.capability_score,reverse=True)[:10]
        return {'civilization_id':self.civilization_id,'tick':self.tick,'generation':self.generation,'agents':len(self.agents),'ideas':len(self.global_ideas),'messages':len(self.network.memory.messages),'research':self.research.snapshot(),'bureau':self.bureau.snapshot(),'society':self.society.snapshot(),'emergence':self.emergence.snapshot(),'evolution':self.evolution.snapshot(),'arena':self.arena.snapshot(),'best_agents':[{'id':a.agent_id,'archetype':a.archetype,'capability':round(a.intelligence.capability_score,3),'experience':a.intelligence.experience,'discoveries':a.intelligence.discoveries} for a in best],'top_ideas':[{'title':i.title,'origin':i.origin,'fitness':round(i.fitness,4),'real_score':round(i.validation_score,6),'return':round(i.validation_return,6),'drawdown':round(i.validation_drawdown,6),'samples':i.validation_samples,'passed':i.validation_passed} for i in top],'events':self.events[-20:]}
