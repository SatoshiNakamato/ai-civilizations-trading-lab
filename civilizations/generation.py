"""Generation lifecycle tying tournament selection to lineage reproduction."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import time
from typing import Iterable

from .evolution import EvolutionEngine, Survivor
from .lineage import LineageLedger
from .tournament import CivilizationTournament, TournamentRecord


@dataclass(frozen=True)
class GenerationRecord:
    generation: int
    tournament_id: str
    parents: tuple[str, ...]
    children: tuple[str, ...]
    created_at: float
    record_hash: str


class GenerationEngine:
    """Advance one generation only from an auditable tournament result."""

    def __init__(self, tournament: CivilizationTournament, *, lineage: LineageLedger | None = None) -> None:
        self.tournament = tournament
        self.lineage = lineage or LineageLedger()
        self.evolution = EvolutionEngine(self.lineage)
        self.records: list[GenerationRecord] = []

    def advance(self, tournament_record: TournamentRecord, *, offspring_per_parent: int = 1, created_at: float | None = None) -> GenerationRecord:
        if tournament_record.generation < 1:
            raise ValueError("generation must be positive")
        if tournament_record.tournament_id not in self.tournament.records:
            raise ValueError("tournament record is not owned by this engine")
        if not tournament_record.selected:
            raise ValueError("cannot evolve without selected parents")
        now = time() if created_at is None else created_at
        survivors = tuple(Survivor(cid, next(score for name, score, _ in tournament_record.rankings if name == cid)) for cid in tournament_record.selected)
        children = self.evolution.reproduce(survivors, generation=tournament_record.generation + 1, offspring_per_parent=offspring_per_parent, created_at=now)
        child_ids = tuple(x.civilization_id for x in children)
        payload = f"{tournament_record.record_hash}|{tournament_record.generation}|{tournament_record.selected}|{child_ids}|{now:.6f}"
        record = GenerationRecord(tournament_record.generation + 1, tournament_record.tournament_id, tournament_record.selected, child_ids, now, sha256(payload.encode()).hexdigest())
        self.records.append(record)
        return record
