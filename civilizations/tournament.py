"""Auditable tournament records for the AEON Civilization Arena."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import time
from typing import Iterable

from .arena import CivilizationArena
from .fitness import FitnessPolicy
from .scoring import score_forecast
from .selection import rank_civilizations


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
    """Records evidence-gated competition using one explicit fitness policy."""

    def __init__(self, arena: CivilizationArena, *, policy: FitnessPolicy | None = None) -> None:
        self.arena = arena
        self.policy = policy or FitnessPolicy()
        self.records: dict[str, TournamentRecord] = {}

    def _ranking(self, participants: tuple[str, ...]):
        score_map = {}
        for cid in participants:
            rows = self.arena._scores(cid)
            score_map[cid] = [score_forecast(probability, outcome) for probability, outcome in rows]
        return rank_civilizations(score_map, policy=self.policy)

    def run(self, civilization_ids: Iterable[str], *, survivors: int, generation: int, tournament_id: str | None = None) -> TournamentRecord:
        if survivors < 1:
            raise ValueError("survivors must be positive")
        participants = tuple(dict.fromkeys(civilization_ids))
        if not participants:
            raise ValueError("at least one civilization is required")
        board = self._ranking(participants)
        eligible = [x.civilization_id for x in board if x.fitness != float("-inf")]
        selected = tuple(eligible[:survivors])
        excluded = tuple(cid for cid in participants if cid not in selected)
        rankings = tuple((x.civilization_id, x.fitness, x.forecasts) for x in board)
        created_at = time()
        tid = tournament_id or sha256(f"{generation}|{participants}|{created_at:.6f}".encode()).hexdigest()[:24]
        payload = f"{tid}|{generation}|{participants}|{rankings}|{selected}|{excluded}|{created_at:.6f}|{self.policy.version}"
        record_hash = sha256(payload.encode()).hexdigest()
        record = TournamentRecord(tid, generation, participants, rankings, selected, excluded, created_at, record_hash)
        self.records[tid] = record
        return record

    def get(self, tournament_id: str) -> TournamentRecord:
        return self.records[tournament_id]

    def snapshot(self) -> dict:
        return {"tournaments": len(self.records), "policy_version": self.policy.version, "records": [{"tournament_id": r.tournament_id, "generation": r.generation, "participants": list(r.participants), "selected": list(r.selected), "excluded": list(r.excluded), "record_hash": r.record_hash} for r in self.records.values()]}
