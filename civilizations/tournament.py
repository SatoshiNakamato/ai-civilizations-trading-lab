"""Auditable tournament records for the AEON Civilization Arena."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import time
from typing import Iterable

from .arena import CivilizationArena, CivilizationScore, SelectionResult


@dataclass(frozen=True)
class TournamentRecord:
    tournament_id: str
    generation: int
    participants: tuple[str, ...]
    rankings: tuple[tuple[str, float, int], ...]
    selected: tuple[str, ...]
    excluded: tuple[str, ...]
    created_at: float
    record_hash: str


class CivilizationTournament:
    """Records evidence-gated competition without fabricating fitness."""

    def __init__(self, arena: CivilizationArena) -> None:
        self.arena = arena
        self.records: dict[str, TournamentRecord] = {}

    def run(self, civilization_ids: Iterable[str], *, survivors: int, generation: int, tournament_id: str | None = None) -> TournamentRecord:
        participants = tuple(dict.fromkeys(civilization_ids))
        if not participants:
            raise ValueError("at least one civilization is required")
        selection: SelectionResult = self.arena.select(participants, survivors=survivors, generation=generation)
        board = self.arena.leaderboard(participants)
        rankings = tuple((s.civilization_id, s.fitness, s.resolved) for s in board)
        created_at = time()
        tid = tournament_id or sha256(f"{generation}|{participants}|{created_at:.6f}".encode()).hexdigest()[:24]
        payload = f"{tid}|{generation}|{participants}|{rankings}|{selection.selected}|{selection.excluded}|{created_at:.6f}"
        record_hash = sha256(payload.encode()).hexdigest()
        record = TournamentRecord(tid, generation, participants, rankings, selection.selected, selection.excluded, created_at, record_hash)
        self.records[tid] = record
        return record

    def get(self, tournament_id: str) -> TournamentRecord:
        return self.records[tournament_id]

    def snapshot(self) -> dict:
        return {"tournaments": len(self.records), "records": [{"tournament_id": r.tournament_id, "generation": r.generation, "participants": list(r.participants), "selected": list(r.selected), "excluded": list(r.excluded), "record_hash": r.record_hash} for r in self.records.values()]}
