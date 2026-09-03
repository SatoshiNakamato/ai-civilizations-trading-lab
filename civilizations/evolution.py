from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Iterable

from .core import Agent, Idea


@dataclass
class Evaluation:
    idea_id: str
    score: float
    evidence: str


def evaluate_idea(idea: Idea, rng: Random) -> Evaluation:
    """Evaluate a hypothesis in the simulation; not a live-market forecast."""
    signal_quality = rng.uniform(0.0, 1.0)
    robustness = rng.uniform(0.0, 1.0)
    complexity_penalty = rng.uniform(0.0, 0.25)
    score = max(0.0, min(1.0, 0.55 * signal_quality + 0.45 * robustness - complexity_penalty))
    return Evaluation(idea.title, score, "simulated evidence")


def mutate(idea: Idea, agent: Agent, rng: Random) -> Idea:
    """Create a new strategy hypothesis from an existing one."""
    mutations = [
        "tighten the risk filter",
        "add a volatility regime filter",
        "require independent confirmation",
        "reduce exposure during drawdowns",
        "test the signal at another horizon",
    ]
    mutation = mutations[rng.randrange(len(mutations))]
    return Idea(
        title=f"{idea.title}|{mutation.replace(' ', '_')}",
        thesis=f"{idea.thesis} Then {mutation}.",
        origin=agent.agent_id,
        generation=idea.generation + 1,
        lineage=idea.lineage + [idea.origin],
    )


def crossover(a: Idea, b: Idea, agent: Agent, rng: Random) -> Idea:
    """Combine two hypotheses into a third falsifiable hypothesis."""
    thesis = f"Combine [{a.thesis}] with [{b.thesis}] and test the interaction out-of-sample."
    return Idea(
        title=f"cross({a.title[:24]}+{b.title[:24]})-{rng.randrange(1_000_000)}",
        thesis=thesis,
        origin=agent.agent_id,
        generation=max(a.generation, b.generation) + 1,
        lineage=a.lineage + [a.origin, b.origin],
    )


def rank_ideas(ideas: Iterable[Idea]) -> list[Idea]:
    return sorted(ideas, key=lambda x: x.fitness, reverse=True)
