from __future__ import annotations

from dataclasses import dataclass, asdict
from random import Random
from time import time
from typing import Iterable


@dataclass
class StrategyMeme:
    meme_id: str
    name: str
    thesis: str
    origin: str
    generation: int
    fitness: float = 0.0
    carriers: int = 1
    mutations: int = 0
    support: int = 0
    challenges: int = 0


@dataclass
class Organization:
    org_id: str
    name: str
    founder: str
    mission: str
    members: list[str]
    treasury: float = 0.0
    influence: float = 0.0


class EmergenceEngine:
    """The social/economic layer that turns agents into a living civilization.

    Strategies are represented as bounded information objects. They can be
    copied, challenged, mutated and recombined inside the simulation; they do
    not execute code or replicate outside the simulation.
    """

    MISSIONS = (
        "compound knowledge",
        "protect capital",
        "discover new markets",
        "maximize evidence quality",
        "build cooperative advantage",
    )

    def __init__(self, seed: int = 42):
        self.rng = Random(seed)
        self.generation = 0
        self.memes: dict[str, StrategyMeme] = {}
        self.organizations: dict[str, Organization] = {}
        self.events: list[dict] = []
        self.discovery_points = 0.0
        self.innovation_points = 0.0
        self.social_capital = 0.0

    def seed_population(self, agents: Iterable) -> None:
        for agent in agents:
            self._ensure_meme(agent.agent_id, agent.archetype, f"{agent.archetype} research doctrine")

    def _ensure_meme(self, agent_id: str, archetype: str, thesis: str) -> StrategyMeme:
        meme_id = f"M-{agent_id}-{archetype}"
        if meme_id not in self.memes:
            self.memes[meme_id] = StrategyMeme(meme_id, f"{archetype}-doctrine", thesis, agent_id, self.generation)
        return self.memes[meme_id]

    def observe(self, agent, idea, peers: list, tick: int) -> None:
        source = self._ensure_meme(agent.agent_id, agent.archetype, idea.thesis)
        source.fitness = max(source.fitness, float(idea.fitness))
        source.carriers = max(1, source.carriers)
        self.discovery_points += max(0.0, idea.fitness)

        if peers:
            peer = self.rng.choice(peers)
            inherited = self.rng.random() < min(0.95, 0.20 + agent.cooperation * 0.55)
            if inherited:
                source.carriers += 1
                self.social_capital += 0.25
                self._record(tick, "idea_adopted", agent.agent_id, peer.agent_id, source.meme_id)

        if self.rng.random() < agent.curiosity * 0.30:
            mutation_id = f"MUT-{tick}-{agent.agent_id}-{self.rng.randrange(1_000_000)}"
            mutation = StrategyMeme(
                mutation_id,
                f"mutation-{agent.archetype}",
                f"{idea.thesis} | mutation: test an alternative horizon and stricter evidence threshold",
                agent.agent_id,
                self.generation + 1,
                fitness=idea.fitness * 0.9,
                mutations=1,
            )
            self.memes[mutation_id] = mutation
            self.innovation_points += 1.0
            self._record(tick, "idea_mutated", agent.agent_id, None, mutation_id)

    def form_organizations(self, agents: Iterable, tick: int) -> None:
        agents = list(agents)
        if len(agents) < 3:
            return
        leaders = sorted(agents, key=lambda a: (a.reputation + a.cooperation + a.curiosity), reverse=True)[:5]
        for index, leader in enumerate(leaders):
            org_id = f"ORG-{self.generation:04d}-{index + 1:02d}"
            if org_id in self.organizations:
                continue
            candidates = [a for a in agents if a.agent_id != leader.agent_id and a.archetype != leader.archetype]
            members = [leader.agent_id] + [a.agent_id for a in self.rng.sample(candidates, min(4, len(candidates)))]
            mission = self.rng.choice(self.MISSIONS)
            org = Organization(org_id, f"{mission.title()} Guild", leader.agent_id, mission, members,
                               treasury=100.0 + leader.reputation * 50.0,
                               influence=min(1.0, 0.25 + leader.cooperation * 0.5))
            self.organizations[org_id] = org
            self._record(tick, "organization_formed", leader.agent_id, None, org_id)

    def economic_tick(self, agents: Iterable, tick: int) -> None:
        agents = list(agents)
        if not agents:
            return
        active = max(1, len(self.organizations))
        for org in self.organizations.values():
            productivity = sum(next((a.intelligence.capability_score for a in agents if a.agent_id == m), 0.0) for m in org.members)
            org.treasury += 1.0 + productivity * 0.05
            org.influence = min(1.0, org.influence + 0.002 * len(org.members))
        self.social_capital = min(1000.0, self.social_capital + active * 0.05)
        self.discovery_points *= 0.995
        self.innovation_points *= 0.998

    def advance(self, agents: Iterable, tick: int) -> None:
        self.form_organizations(agents, tick)
        self.economic_tick(agents, tick)
        self.generation += 1
        self.events = self.events[-250:]

    def _record(self, tick: int, event: str, actor: str, target: str | None, object_id: str) -> None:
        self.events.append({"tick": tick, "generation": self.generation, "event": event,
                            "actor": actor, "target": target, "object": object_id, "at": time()})

    def snapshot(self) -> dict:
        top = sorted(self.memes.values(), key=lambda x: (x.fitness, x.carriers, x.support - x.challenges), reverse=True)[:15]
        return {
            "generation": self.generation,
            "memes": len(self.memes),
            "organizations": len(self.organizations),
            "discovery_points": round(self.discovery_points, 3),
            "innovation_points": round(self.innovation_points, 3),
            "social_capital": round(self.social_capital, 3),
            "top_memes": [asdict(m) for m in top],
            "organizations_state": [asdict(o) for o in self.organizations.values()],
            "events": self.events[-30:],
        }
