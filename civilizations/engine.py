"""End-to-end, evidence-only Civilization Arena generation cycle."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import time
from typing import Iterable

from .arena import CivilizationArena
from .audit import AuditLedger
from .generation import GenerationEngine, GenerationRecord
from .tournament import CivilizationTournament, TournamentRecord


@dataclass(frozen=True)
class CycleResult:
    tournament: TournamentRecord
    generation: GenerationRecord
    audit_head: str


class CivilizationCycle:
    """Run one real generation transition from already-recorded evidence.

    No synthetic forecasts, prices, or outcomes are created here. Market data and
    civilization forecasts must enter through the existing Arena/provider boundaries.
    """

    def __init__(self, arena: CivilizationArena, *, audit: AuditLedger | None = None) -> None:
        self.arena = arena
        self.tournament = CivilizationTournament(arena)
        self.generation = GenerationEngine(self.tournament)
        self.audit = audit or AuditLedger()

    def run(self, civilization_ids: Iterable[str], *, survivors: int, generation: int, offspring_per_parent: int = 1, tournament_id: str | None = None, created_at: float | None = None) -> CycleResult:
        ids = tuple(dict.fromkeys(civilization_ids))
        if generation < 1:
            raise ValueError("generation must be positive")
        if not ids:
            raise ValueError("at least one civilization is required")
        if survivors > len(ids):
            raise ValueError("survivors cannot exceed participants")
        now = time() if created_at is None else float(created_at)
        tournament = self.tournament.run(ids, survivors=survivors, generation=generation, tournament_id=tournament_id)
        self.audit.append("tournament.completed", {
            "tournament_id": tournament.tournament_id,
            "generation": generation,
            "participants": list(tournament.participants),
            "selected": list(tournament.selected),
            "record_hash": tournament.record_hash,
        })
        if not tournament.selected:
            raise ValueError("no evidence-qualified civilization survived")
        next_generation = self.generation.advance(tournament, offspring_per_parent=offspring_per_parent, created_at=now)
        self.audit.append("generation.created", {
            "generation": next_generation.generation,
            "tournament_id": next_generation.tournament_id,
            "parents": list(next_generation.parents),
            "children": list(next_generation.children),
            "record_hash": next_generation.record_hash,
        })
        head = self.audit.entries()[-1].entry_hash
        return CycleResult(tournament, next_generation, head)

    def identity(self, result: CycleResult) -> str:
        return sha256(f"{result.tournament.record_hash}|{result.generation.record_hash}|{result.audit_head}".encode()).hexdigest()
