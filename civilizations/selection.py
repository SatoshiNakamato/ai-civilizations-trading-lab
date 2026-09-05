"""Policy-driven ranking for civilization tournaments."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .fitness import FitnessPolicy
from .scoring import ForecastScore


@dataclass(frozen=True)
class RankedCivilization:
    civilization_id: str
    fitness: float
    forecasts: int


def rank_civilizations(
    scores_by_civilization: Mapping[str, Iterable[ForecastScore]],
    *,
    policy: FitnessPolicy | None = None,
) -> tuple[RankedCivilization, ...]:
    """Rank civilizations using one explicit policy and deterministic tie-breaking."""
    active_policy = policy or FitnessPolicy()
    ranked: list[RankedCivilization] = []
    for civilization_id, scores in scores_by_civilization.items():
        values = list(scores)
        ranked.append(RankedCivilization(civilization_id, active_policy.evaluate(values), len(values)))
    return tuple(sorted(ranked, key=lambda x: (-x.fitness, -x.forecasts, x.civilization_id)))
