from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Dict, List


ARCHETYPES = [
    ("quant", "Quant Researcher"),
    ("arb", "Arbitrage Hunter"),
    ("macro", "Macro Analyst"),
    ("momentum", "Momentum Trader"),
    ("value", "Value Researcher"),
    ("contrarian", "Contrarian"),
    ("risk", "Risk Manager"),
    ("probability", "Prediction-Market Analyst"),
    ("microstructure", "Market Microstructure Specialist"),
    ("explorer", "Strategy Explorer"),
]


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

    ideas: List[Idea] = field(default_factory=list)

    wealth_score: float = 0.0
    age: int = 0

    def observe_and_propose(self, tick: int, rng: Random) -> Idea:
        themes = {
            "quant": (
                "Test a statistical relationship and demand "
                "out-of-sample confirmation."
            ),
            "arb": (
                "Search for temporary cross-market price discrepancies "
                "after fees, slippage and latency."
            ),
            "macro": (
                "Map macroeconomic regime changes to asset behavior."
            ),
            "momentum": (
                "Test price persistence while accounting for liquidity "
                "and transaction costs."
            ),
            "value": (
                "Compare market price with a conservative fair-value estimate."
            ),
            "contrarian": (
                "Look for crowded positioning and asymmetric reversal setups."
            ),
            "risk": (
                "Improve position sizing using volatility, correlation "
                "and drawdown information."
            ),
            "probability": (
                "Compare implied event probabilities with calibrated "
                "forecast probabilities."
            ),
            "microstructure": (
                "Study spreads, liquidity and order-flow dynamics."
            ),
            "explorer": (
                "Combine two unrelated signals into a falsifiable hypothesis."
            ),
        }

        title = (
            f"{self.archetype}-idea-"
            f"{tick}-"
            f"{rng.randrange(1_000_000)}"
        )

        return Idea(
            title=title,
            thesis=themes[self.archetype],
            origin=self.agent_id,
            generation=tick,
        )

    def evaluate(self, idea: Idea, rng: Random) -> float:
        """
        Simulation fitness only.

        This is deliberately NOT presented as a prediction of
        real-world trading profitability.
        """

        noise = rng.gauss(0, 0.15)

        base = (
            0.45 * self.curiosity
            + 0.35 * self.cooperation
            + 0.20 * self.risk_tolerance
        )

        idea.fitness = max(
            -1.0,
            min(1.0, base + noise)
        )

        return idea.fitness


class Civilization:

    def __init__(
        self,
        size: int = 100,
        seed: int = 42,
    ):
        self.rng = Random(seed)

        self.tick = 0
        self.generation = 0

        self.agents: Dict[str, Agent] = {}

        self.global_ideas: List[Idea] = []

        self.events: List[str] = []

        self._create_population(size)

    # ---------------------------------------------------------
    # POPULATION
    # ---------------------------------------------------------

    def _create_population(self, size: int) -> None:

        for i in range(size):

            archetype_key, role = ARCHETYPES[
                i % len(ARCHETYPES)
            ]

            sex = "female" if i % 2 else "male"

            agent = Agent(
                agent_id=f"A{i + 1:03d}",
                name=f"{role} {i + 1:03d}",
                archetype=archetype_key,
                sex=sex,

                risk_tolerance=self.rng.random(),
                curiosity=self.rng.random(),
                cooperation=self.rng.random(),
            )

            self.agents[agent.agent_id] = agent

    # ---------------------------------------------------------
    # MAIN LIFE CYCLE
    # ---------------------------------------------------------

    def step(self) -> dict:

        self.tick += 1

        # 1. Every agent observes and proposes an idea.
        proposals = []

        for agent in self.agents.values():

            idea = agent.observe_and_propose(
                self.tick,
                self.rng,
            )

            proposals.append(idea)

        # 2. Agents evaluate their own hypotheses.
        for idea in proposals:

            agent = self.agents[idea.origin]

            agent.evaluate(
                idea,
                self.rng,
            )

        # 3. Select promising ideas.
        ranked = sorted(
            proposals,
            key=lambda x: x.fitness,
            reverse=True,
        )

        # 4. Share ideas between agents.
        #
        # This is the controlled version of the
        # "mind virus" concept:
        #
        # ideas can spread and mutate,
        # but software/code cannot self-replicate.
        #
        for idea in ranked[:20]:

            peers = self._sample_peers(
                idea.origin,
                2,
            )

            for agent in peers:

                if self.rng.random() < agent.cooperation:

                    child = Idea(
                        title=f"{idea.title}-m{self.tick}",
                        thesis=idea.thesis,
                        origin=agent.agent_id,
                        generation=self.tick,
                        lineage=(
                            idea.lineage
                            + [idea.origin]
                        ),
                    )

                    agent.ideas.append(child)

                    self.global_ideas.append(child)

        # 5. Civilization advances.
        self.generation += 1

        event = (
            f"tick={self.tick}: "
            f"{len(proposals)} hypotheses generated; "
            f"{min(20, len(ranked))} selected for exchange"
        )

        self.events.append(event)

        # Keep memory bounded.
        self.events = self.events[-100:]

        return self.snapshot()

    # ---------------------------------------------------------
    # SOCIAL NETWORK
    # ---------------------------------------------------------

    def _sample_peers(
        self,
        origin: str,
        count: int,
    ):

        pool = [
            agent
            for agent_id, agent in self.agents.items()
            if agent_id != origin
        ]

        self.rng.shuffle(pool)

        return pool[:count]

    # ---------------------------------------------------------
    # STATE
    # ---------------------------------------------------------

    def snapshot(self) -> dict:

        top = sorted(
            self.global_ideas,
            key=lambda x: x.fitness,
            reverse=True,
        )[:10]

        return {
            "tick": self.tick,

            "generation": self.generation,

            "agents": len(self.agents),

            "ideas": len(self.global_ideas),

            "top_ideas": [
                {
                    "title": idea.title,
                    "origin": idea.origin,
                    "fitness": round(
                        idea.fitness,
                        4,
                    ),
                    "generation": idea.generation,
                }
                for idea in top
            ],

            "events": self.events[-20:],
        }


if __name__ == "__main__":

    civilization = Civilization(
        size=100,
        seed=42,
    )

    print("AI CIVILIZATION ONLINE")
    print("======================")

    print(
        f"Population: {len(civilization.agents)}"
    )

    for _ in range(10):

        state = civilization.step()

        print(
            f"\nGeneration {state['generation']}"
        )

        print(
            f"Ideas discovered: {state['ideas']}"
        )

        if state["top_ideas"]:

            best = state["top_ideas"][0]

            print(
                "Best idea:",
                best["title"],
                "| fitness:",
                best["fitness"],
            )
