"""Production-oriented runtime orchestration for AEON civilizations."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Mapping

from .anti_gaming import ForecastKey, validate_forecast_batch
from .audit import AuditLedger
from .engine import CivilizationCycle, CycleResult
from .release import ReleaseChecklist


@dataclass(frozen=True)
class RuntimeConfig:
    survivors: int
    generation: int
    offspring_per_parent: int = 1


@dataclass(frozen=True)
class RuntimeResult:
    run_id: str
    cycle: CycleResult
    audit_valid: bool


class CivilizationRuntime:
    """Single bounded execution step; external evidence remains mandatory."""

    def __init__(self, cycle: CivilizationCycle, *, checklist: ReleaseChecklist | None = None) -> None:
        self.cycle = cycle
        self.checklist = checklist or ReleaseChecklist()

    @staticmethod
    def run_id(generation: int, civilization_ids: Iterable[str], markets: Iterable[str]) -> str:
        payload = f"{generation}|{tuple(civilization_ids)}|{tuple(markets)}"
        return sha256(payload.encode()).hexdigest()[:24]

    def validate_forecasts(self, forecasts: Iterable[ForecastKey], *, max_per_market: int = 1) -> tuple[ForecastKey, ...]:
        return validate_forecast_batch(tuple(forecasts), max_per_market=max_per_market)

    def step(self, civilization_ids: Iterable[str], *, config: RuntimeConfig, markets: Iterable[str] = ()) -> RuntimeResult:
        ids = tuple(dict.fromkeys(civilization_ids))
        market_tuple = tuple(dict.fromkeys(markets))
        rid = self.run_id(config.generation, ids, market_tuple)
        cycle = self.cycle.run(ids, survivors=config.survivors, generation=config.generation, offspring_per_parent=config.offspring_per_parent, tournament_id=f"runtime-{rid}")
        audit_valid = self.cycle.audit.verify()
        if not audit_valid:
            raise RuntimeError("runtime audit verification failed")
        return RuntimeResult(rid, cycle, audit_valid)
