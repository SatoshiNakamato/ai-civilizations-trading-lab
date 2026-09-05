from __future__ import annotations

from dataclasses import dataclass
from random import Random

from .core import Civilization
from .internet_world import InternetWorld
from .life_engine import LifeEngine


@dataclass
class Deployment:
    agent_id: str
    kind: str
    purpose: str
    artifact: str
    status: str = "created"


class AEONRuntime:
    """Runs a persistent civilization as a digital world.

    Agents receive continuity, needs, relationships, reflection and bounded
    self-deployment. Web access is mediated by InternetWorld; artifacts are
    inert until an external operator explicitly executes them.
    """

    def __init__(self, size: int = 100, seed: int = 42, artifact_root: str = "world_artifacts"):
        self.civilization = Civilization(size=size, seed=seed)
        self.life = LifeEngine(seed=seed)
        self.world = InternetWorld(root=artifact_root)
        self.rng = Random(seed)
        self.deployments: list[Deployment] = []
        for agent in self.civilization.agents.values():
            self.life.register(agent.agent_id, [agent.archetype, "curiosity", "survival", "growth"])

    def _autonomous_project(self, agent) -> Deployment | None:
        """Let an agent choose a project from its internal state."""
        state = self.life.states[agent.agent_id]
        if state.energy < 0.25 or state.curiosity < 0.2:
            return None
        choices = [
            ("research_node", "investigate an unanswered question"),
            ("knowledge_artifact", "preserve a useful discovery"),
            ("strategy_lab", "test a new strategy hypothesis"),
            ("social_institution", "create a cooperative institution"),
        ]
        kind, purpose = choices[self.rng.randrange(len(choices))]
        content = f"# {kind}\nagent={agent.agent_id}\npurpose={purpose}\ngeneration={self.civilization.generation}\n"
        path = self.world.create_artifact(agent.agent_id, f"{agent.agent_id}/{kind}-{self.civilization.tick}.md", content)
        deployment = Deployment(agent.agent_id, kind, purpose, path)
        self.deployments.append(deployment)
        self.life.remember(agent.agent_id, self.civilization.tick, f"Created {kind}: {purpose}", "discovery", 0.75)
        return deployment

    def step(self) -> dict:
        state = self.civilization.step()
        for agent in self.civilization.agents.values():
            self.life.experience(agent.agent_id, self.civilization.tick, agent.intelligence.capability_score, agent.curiosity)
            if self.civilization.tick % 5 == 0:
                self.life.reflect(agent.agent_id, self.civilization.tick)
            if self.rng.random() < min(0.25, 0.02 + agent.curiosity * 0.08):
                self._autonomous_project(agent)
        ids = list(self.civilization.agents)
        for _ in range(min(8, len(ids) // 2)):
            a, b = self.rng.sample(ids, 2)
            self.life.interact(a, b, self.civilization.tick, self.rng.uniform(-1, 1))
        state["life"] = self.life.snapshot(ids)
        state["world"] = self.world.snapshot()
        state["deployments"] = [d.__dict__ for d in self.deployments[-20:]]
        return state

    def run(self, steps: int = 1) -> dict:
        snapshot = {}
        for _ in range(max(1, steps)):
            snapshot = self.step()
        return snapshot


if __name__ == "__main__":
    world = AEONRuntime()
    print(world.run(3))
