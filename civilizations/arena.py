"""Objective evaluation and selection for the AEON Civilization Arena."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import time
from typing import Iterable


@dataclass(frozen=True)
class ForecastCommitment:
    forecast_id: str
    civilization_id: str
    agent_id: str
    market: str
    horizon: str
    probability: float
    created_at: float
    commitment: str
    resolved: bool = False


@dataclass(frozen=True)
class ForecastOutcome:
    forecast_id: str
    event: bool
    observed_at: float
    source: str


@dataclass
class CivilizationScore:
    civilization_id: str
    forecasts: int = 0
    resolved: int = 0
    brier_score: float | None = None
    calibration_error: float | None = None
    resolution_rate: float = 0.0
    fitness: float = 0.0
    sample_sufficient: bool = False


@dataclass
class ArenaConfig:
    min_resolved: int = 20
    max_abs_probability: float = 1.0
    log_loss_floor: float = 1e-6


@dataclass(frozen=True)
class SelectionResult:
    selected: tuple[str, ...]
    excluded: tuple[str, ...]
    generation: int


class CivilizationArena:
    """Real evaluation ledger and selection boundary for civilizations.

    Forecasts are immutable commitments. Outcomes are supplied separately by an
    external resolver. Selection is sample-gated so an untested civilization cannot
    win merely by having a lucky first observation.
    """

    def __init__(self, config: ArenaConfig | None = None) -> None:
        self.config = config or ArenaConfig()
        self.commitments: dict[str, ForecastCommitment] = {}
        self.outcomes: dict[str, ForecastOutcome] = {}
        self._by_civilization: dict[str, list[str]] = {}

    @staticmethod
    def commit(civilization_id: str, agent_id: str, market: str, horizon: str, probability: float, *, forecast_id: str | None = None, created_at: float | None = None) -> ForecastCommitment:
        if not civilization_id or not agent_id or not market or not horizon:
            raise ValueError("civilization_id, agent_id, market and horizon are required")
        if not 0.0 <= probability <= 1.0:
            raise ValueError("probability must be between 0 and 1")
        ts = time() if created_at is None else float(created_at)
        fid = forecast_id or sha256(f"{civilization_id}:{agent_id}:{market}:{horizon}:{ts}".encode()).hexdigest()[:24]
        payload = f"{fid}|{civilization_id}|{agent_id}|{market}|{horizon}|{probability:.12f}|{ts:.6f}"
        digest = sha256(payload.encode()).hexdigest()
        return ForecastCommitment(fid, civilization_id, agent_id, market, horizon, probability, ts, digest)

    def submit(self, commitment: ForecastCommitment) -> ForecastCommitment:
        if commitment.forecast_id in self.commitments:
            existing = self.commitments[commitment.forecast_id]
            if existing.commitment != commitment.commitment:
                raise ValueError("forecast_id collision with different commitment")
            return existing
        self.commitments[commitment.forecast_id] = commitment
        self._by_civilization.setdefault(commitment.civilization_id, []).append(commitment.forecast_id)
        return commitment

    def resolve(self, outcome: ForecastOutcome) -> ForecastOutcome:
        commitment = self.commitments.get(outcome.forecast_id)
        if commitment is None:
            raise KeyError(f"unknown forecast: {outcome.forecast_id}")
        if outcome.forecast_id in self.outcomes:
            existing = self.outcomes[outcome.forecast_id]
            if existing != outcome:
                raise ValueError("forecast already resolved with a different outcome")
            return existing
        if outcome.observed_at < commitment.created_at:
            raise ValueError("outcome timestamp cannot precede forecast commitment")
        if not outcome.source.strip():
            raise ValueError("an external outcome source is required")
        self.outcomes[outcome.forecast_id] = outcome
        return outcome

    def record_prediction(self, civilization_id: str, market: str, probability: float, event: bool, *, agent_id: str = "arena", horizon: str = "default", created_at: float | None = None, observed_at: float | None = None, source: str = "arena") -> ForecastCommitment:
        """Convenience boundary for recording a forecast and its known testable outcome."""
        commitment = self.commit(civilization_id, agent_id, market, horizon, probability, created_at=created_at)
        self.submit(commitment)
        observed = commitment.created_at if observed_at is None else float(observed_at)
        self.resolve(ForecastOutcome(commitment.forecast_id, bool(event), observed, source))
        return commitment

    def _scores(self, civilization_id: str) -> list[tuple[float, bool]]:
        return [(self.commitments[fid].probability, self.outcomes[fid].event) for fid in self._by_civilization.get(civilization_id, []) if fid in self.outcomes]

    def score(self, civilization_id: str) -> CivilizationScore:
        forecasts = len(self._by_civilization.get(civilization_id, []))
        rows = self._scores(civilization_id)
        resolved = len(rows)
        if not rows:
            return CivilizationScore(civilization_id, forecasts=forecasts)
        brier = sum((p - float(event)) ** 2 for p, event in rows) / resolved
        bins: dict[int, list[tuple[float, bool]]] = {}
        for p, event in rows:
            bins.setdefault(min(9, int(p * 10)), []).append((p, event))
        calibration = sum(abs(sum(p for p, _ in bucket) / len(bucket) - sum(float(e) for _, e in bucket) / len(bucket)) for bucket in bins.values()) / len(bins)
        resolution_rate = resolved / forecasts if forecasts else 0.0
        fitness = 0.6 * max(0.0, 1.0 - brier) + 0.3 * max(0.0, 1.0 - calibration) + 0.1 * resolution_rate
        return CivilizationScore(civilization_id, forecasts, resolved, brier, calibration, resolution_rate, fitness, resolved >= self.config.min_resolved)

    def leaderboard(self, civilization_ids: Iterable[str] | None = None) -> list[CivilizationScore]:
        ids = list(civilization_ids) if civilization_ids is not None else list(self._by_civilization)
        return sorted((self.score(cid) for cid in ids), key=lambda s: (s.sample_sufficient, s.fitness, s.resolved), reverse=True)

    def select(self, civilization_ids: Iterable[str], *, survivors: int, generation: int) -> SelectionResult:
        if survivors < 1:
            raise ValueError("survivors must be positive")
        board = self.leaderboard(civilization_ids)
        eligible = [s.civilization_id for s in board if s.sample_sufficient]
        selected = tuple(eligible[:survivors])
        excluded = tuple(cid for cid in civilization_ids if cid not in selected)
        return SelectionResult(selected, excluded, generation)

    def snapshot(self) -> dict:
        board = self.leaderboard()
        return {"commitments": len(self.commitments), "resolved": len(self.outcomes), "civilizations": len(self._by_civilization), "leaderboard": [{"rank": i + 1, "civilization_id": s.civilization_id, "forecasts": s.forecasts, "resolved": s.resolved, "brier_score": None if s.brier_score is None else round(s.brier_score, 6), "calibration_error": None if s.calibration_error is None else round(s.calibration_error, 6), "fitness": round(s.fitness, 6), "sample_sufficient": s.sample_sufficient} for i, s in enumerate(board)]}
