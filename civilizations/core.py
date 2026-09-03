from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Dict, List

from .communication import CommunicationNetwork
from .evolution import crossover, evaluate_idea, mutate, rank_ideas
from .learning import Intelligence
from .research import PublicWebCollector, ResearchDesk
from .research_bridge import ResearchBridge
from .research_bureau import ResearchBureau
from .society import Society

ARCHETYPES = [("quant", "Quant Researcher"), ("arb", "Arbitrage Hunter"), ("macro", "Macro Analyst"), ("momentum", "Momentum Trader"), ("value", "Value Researcher"), ("contrarian", "Contrarian"), ("risk", "Risk Manager"), ("probability", "Prediction-Market Analyst"), ("microstructure", "Market Microstructure Specialist"), ("explorer", "Strategy Explorer")]

@dataclass
class Idea:
    title: str
    thesis: str
    origin: str
    fitness: float = 0.0
    generation: int = 0
    lineage: List[str] = field(default_factory=list)

@dataclass
class Agent:
    agent_id: str
    name: str
    archetype: str
    sex: str
    risk_tolerance: float
    curiosity: float
    cooperation: float
    intelligence: Intelligence = field(default_factory=Intelligence)
    ideas: List[Idea] = field(default_factory=list)
    wealth_score: float = 0.0
    reputation: float = 0.0
    age: int = 0
    beliefs: Dict[str, float] = field(default_factory=dict)

    def observe_and_propose(self, tick: int, rng: Random, research_context: dict | None = None) -> Idea:
        themes = {"quant":"Test a statistical relationship and demand out-of-sample confirmation.","arb":"Search for temporary cross-market price discrepancies after fees, slippage and latency.","macro":"Map macroeconomic regime changes to asset behavior.","momentum":"Test price persistence while accounting for liquidity and transaction costs.","value":"Compare market price with a conservative fair-value estimate.","contrarian":"Look for crowded positioning and asymmetric reversal setups.","risk":"Improve position sizing using volatility, correlation and drawdown information.","probability":"Compare implied event probabilities with calibrated forecast probabilities.","microstructure":"Study spreads, liquidity and order-flow dynamics.","explorer":"Combine two unrelated signals into a falsifiable hypothesis."}
        base = themes[self.archetype]
        if research_context and research_context.get("sources"):
            evidence = research_context["sources"][0]["excerpt"][:240]
            base += f" Evidence reviewed: {evidence}"
        return Idea(f"{self.archetype}-idea-{tick}-{rng.randrange(1_000_000)}", base, self.agent_id, generation=tick)

    def evaluate(self, idea: Idea, rng: Random) -> float:
        result = evaluate_idea(idea, rng); idea.fitness = result.score
        self.intelligence.learn_from_research(idea.fitness, min(1.0, 0.35 + self.curiosity * 0.65), min(1.0, 0.25 + self.intelligence.creativity / 500.0))
        return idea.fitness

class Civilization:
    def __init__(self, size: int = 100, seed: int = 42):
        self.rng = Random(seed); self.tick = 0; self.generation = 0
        self.agents: Dict[str, Agent] = {}; self.global_ideas: List[Idea] = []; self.events: List[str] = []
        self.network = CommunicationNetwork(); self.society = Society()
        self.research = ResearchDesk(web_collector=PublicWebCollector())
        self.research_bridge = ResearchBridge(self.research, self.research.web_collector)
        self.bureau = ResearchBureau(self.research.web_collector)
        self._seed_research(); self._create_population(size)

    def _seed_research(self) -> None:
        self.research.ingest("internal://simulation", "Research protocol", "Hypotheses must be falsifiable. Historical success does not guarantee future returns. Transaction costs, liquidity, slippage and out-of-sample validation must be considered.")

    def _create_population(self, size: int) -> None:
        for i in range(size):
            key, role = ARCHETYPES[i % len(ARCHETYPES)]; sex = "female" if i % 2 else "male"
            self.agents[f"A{i+1:03d}"] = Agent(f"A{i+1:03d}", f"{role} {i+1:03d}", key, sex, self.rng.random(), self.rng.random(), self.rng.random())

    def _research_query(self, agent: Agent) -> str:
        return {"quant":"statistical out-of-sample","arb":"price discrepancy transaction costs","macro":"macro economic regime","momentum":"price persistence liquidity","value":"fair value valuation","contrarian":"crowded positioning reversal","risk":"volatility correlation drawdown","probability":"probability forecast calibration","microstructure":"market liquidity spread order flow","explorer":"falsifiable hypothesis validation"}[agent.archetype]

    def step(self) -> dict:
        self.tick += 1; proposals = []
        for agent in self.agents.values():
            query = self._research_query(agent)
            self.bureau.submit_question(agent.agent_id, query, agent.curiosity)
            context = self.research_bridge.build_context(agent.agent_id, query, limit=3)
            idea = agent.observe_and_propose(self.tick, self.rng, context); agent.evaluate(idea, self.rng); agent.ideas.append(idea); self.global_ideas.append(idea)
            finding = self.bureau.investigate(agent.agent_id, query, limit=3)
            finding.confidence = min(1.0, 0.2 + idea.fitness * 0.6)
            self.society.record_knowledge(f"{agent.archetype}:{idea.title}", idea.thesis, agent.agent_id, idea.fitness, self.generation)
            proposals.append(idea)
        champions = rank_ideas(proposals)[:20]
        for idea in champions:
            for peer in self._sample_peers(idea.origin, 3):
                sender = self.agents[idea.origin]; kind = "endorse" if peer.cooperation >= 0.5 else "challenge"
                message = f"{kind}: {idea.title}; thesis={idea.thesis}; fitness={idea.fitness:.3f}"
                self.network.send(sender.agent_id, peer.agent_id, kind, message, self.tick)
                useful = 0.75 if kind == "endorse" else 0.85; self.society.talk(self.generation, sender.agent_id, peer.agent_id, idea.title, message, useful); sender.intelligence.learn_from_collaboration(useful)
                if kind == "endorse": self.society.confirm(idea.title)
                else: self.society.challenge(idea.title)
                self.network.update_reputation(sender.agent_id, 0.01 if idea.fitness >= 0.6 else -0.005)
                if idea.fitness >= 0.55 and self.rng.random() < peer.curiosity:
                    child = mutate(idea, peer, self.rng); peer.evaluate(child, self.rng); peer.ideas.append(child); self.global_ideas.append(child); self.society.record_knowledge(f"{peer.archetype}:{child.title}", child.thesis, peer.agent_id, child.fitness, self.generation)
        if len(champions) >= 2:
            for peer in self._sample_peers("__council__", 5):
                child = crossover(champions[0], champions[1], peer, self.rng); peer.evaluate(child, self.rng); peer.ideas.append(child); self.global_ideas.append(child); self.society.record_knowledge(f"{peer.archetype}:{child.title}", child.thesis, peer.agent_id, child.fitness, self.generation)
        self.generation += 1; self.bureau.generation = self.generation; self.events.append(f"tick={self.tick}: {len(proposals)} web-research-informed hypotheses; {len(champions)} debated; new candidates evolved"); self.events = self.events[-100:]
        return self.snapshot()

    def _sample_peers(self, origin: str, count: int):
        pool = [a for aid,a in self.agents.items() if aid != origin]; self.rng.shuffle(pool); return pool[:count]

    def snapshot(self) -> dict:
        top = sorted(self.global_ideas, key=lambda x:x.fitness, reverse=True)[:10]; best_agents = sorted(self.agents.values(), key=lambda a:a.intelligence.capability_score, reverse=True)[:10]
        return {"tick":self.tick,"generation":self.generation,"agents":len(self.agents),"ideas":len(self.global_ideas),"messages":len(self.network.memory.messages),"research":self.research.snapshot(),"bureau":self.bureau.snapshot(),"society":self.society.snapshot(),"best_agents":[{"id":a.agent_id,"archetype":a.archetype,"capability":round(a.intelligence.capability_score,3),"experience":a.intelligence.experience,"discoveries":a.intelligence.discoveries} for a in best_agents],"top_ideas":[{"title":i.title,"origin":i.origin,"fitness":round(i.fitness,4),"generation":i.generation} for i in top],"events":self.events[-20:]}

if __name__ == "__main__":
    civilization = Civilization(100, 42); print("AI CIVILIZATION ONLINE"); print("======================"); print(f"Population: {len(civilization.agents)}")
    for _ in range(10):
        state=civilization.step(); print(f"\nGeneration {state['generation']}"); print(f"Ideas discovered: {state['ideas']}"); print(f"Messages: {state['messages']}"); print(f"Research documents: {state['research']['documents']}"); print(f"Research findings: {state['bureau']['findings']}"); print(f"Shared knowledge: {state['society']['knowledge_count']}"); print(f"Conversations: {state['society']['conversation_count']}")
        if state['best_agents']:
            a=state['best_agents'][0]; print("Top capability:",a['id'],a['capability'],"experience:",a['experience'])
        if state['top_ideas']:
            i=state['top_ideas'][0]; print("Best idea:",i['title'],"| fitness:",i['fitness'])
