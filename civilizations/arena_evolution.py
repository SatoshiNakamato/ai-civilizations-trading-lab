"""Arena-native civilization lineage and generation management.

This module is intentionally separate from the existing evidence-memory evolution
engine. It governs population transitions only after Arena selection has produced
objective, sample-sufficient survivors.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Callable, Iterable

from .arena import CivilizationArena, SelectionResult


@dataclass(frozen=True)
class CivilizationLineage:
    civilization_id: str
    generation: int
    parent_ids: tuple[str, ...]
    lineage_id: str


@dataclass(frozen=True)
class GenerationRecord:
    generation: int
    population: tuple[str, ...]
    survivors: tuple[str, ...]
    offspring: tuple[str, ...]
    selection: SelectionResult


class ArenaEvolution:
    """Auditable population transitions driven exclusively by Arena selection."""

    def __init__(self, arena: CivilizationArena) -> None:
        self.arena = arena
        self.generation = 0
        self.lineages: dict[str, CivilizationLineage] = {}
        self.history: list[GenerationRecord] = []

    def register(self, civilization_id: str, *, parent_ids: Iterable[str] = ()) -> CivilizationLineage:
        parents = tuple(parent_ids)
        existing = self.lineages.get(civilization_id)
        if existing is not None:
            return existing
        generation = 0 if not parents else self.generation
        lineage_id = sha256(f"{civilization_id}|{generation}|{','.join(parents)}".encode()).hexdigest()[:24]
        item = CivilizationLineage(civilization_id, generation, parents, lineage_id)
        self.lineages[civilization_id] = item
        return item

    def advance(
        self,
        civilization_ids: Iterable[str],
        *,
        survivors: int,
        offspring_factory: Callable[[str, int], str],
    ) -> GenerationRecord:
        population = tuple(civilization_ids)
        selection = self.arena.select(population, survivors=survivors, generation=self.generation)
        offspring = tuple(offspring_factory(parent_id, self.generation + 1) for parent_id in selection.selected)
        for child in offspring:
            self.register(child, parent_ids=selection.selected)
        record = GenerationRecord(self.generation, population, selection.selected, offspring, selection)
        self.history.append(record)
        self.generation += 1
        return record

    def snapshot(self) -> dict:
        return {
            "generation": self.generation,
            "civilizations": len(self.lineages),
            "generations_completed": len(self.history),
            "lineage": [
                {
                    "civilization_id": x.civilization_id,
                    "generation": x.generation,
                    "parent_ids": list(x.parent_ids),
                    "lineage_id": x.lineage_id,
                }
                for x in self.lineages.values()
            ],
        }
