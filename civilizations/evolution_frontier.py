"""Governed frontier layer for civilization self-improvement.

This layer turns research/debate output into durable, replayable evolution
records without granting agents unrestricted source-code or repository access.
It coordinates constitution, diagnostics, experiments, genealogy, mutation
proposals, replay, and command-center state through the existing governor.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from .evolution_governor import EvolutionGovernor


@dataclass(frozen=True)
class FrontierEvent:
    tick: int
    event: str
    agent_id: str
    payload: dict
    timestamp: float


class EvolutionFrontier:
    """Single governed state machine for collective civilization evolution."""

    CONSTITUTION = {
        "source_write": False,
        "external_trade_execution": False,
        "human_review_for_code": True,
        "bounded_resources": True,
        "append_only_history": True,
    }

    def __init__(self, governor: EvolutionGovernor | None = None, root: str | Path | None = None) -> None:
        self.governor = governor or EvolutionGovernor()
        self.root = Path(root or self.governor.root / "frontier").resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_path = self.root / "events.jsonl"
        self.genealogy_path = self.root / "genealogy.jsonl"
        self.replay_path = self.root / "replay.jsonl"
        self.experiments_path = self.root / "experiments.jsonl"

    def _append(self, path: Path, event: FrontierEvent) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(event), sort_keys=True, separators=(",", ":")) + "\n")

    def _event(self, tick: int, event: str, agent_id: str, payload: dict) -> FrontierEvent:
        item = FrontierEvent(tick, event, agent_id, payload, time.time())
        self._append(self.events_path, item)
        self._append(self.replay_path, item)
        return item

    def remember_research(self, tick: int, agent_id: str, topic: str, finding: str, confidence: float) -> None:
        content = json.dumps({"tick": tick, "topic": topic, "finding": finding, "confidence": confidence}, sort_keys=True)
        self.governor.write(agent_id, "memory", f"{agent_id}/research-{tick}.json", content)
        self._event(tick, "research_memory", agent_id, {"topic": topic, "confidence": confidence})

    def record_experiment(self, tick: int, agent_id: str, hypothesis: str, result: str, score: float) -> None:
        event = self._event(tick, "experiment", agent_id, {"hypothesis": hypothesis, "result": result, "score": score})
        self._append(self.experiments_path, event)

    def propose_mutation(self, tick: int, agent_id: str, title: str, rationale: str, patch: str) -> None:
        proposal = self.governor.propose_source_change(agent_id, title, rationale, patch)
        self._event(tick, "mutation_proposal", agent_id, {"path": proposal.path, "sha256": proposal.sha256})

    def record_genealogy(self, tick: int, agent_id: str, parent_ids: Iterable[str], reason: str) -> None:
        payload = {"parents": sorted(set(parent_ids)), "reason": reason}
        event = self._event(tick, "genealogy", agent_id, payload)
        self._append(self.genealogy_path, event)

    def diagnose(self, tick: int, active_ids: Iterable[str], evidence_count: int, debate_count: int) -> dict:
        active = list(active_ids)
        findings = []
        if not active:
            findings.append("no_active_agents")
        if evidence_count == 0:
            findings.append("no_evidence")
        if debate_count == 0:
            findings.append("no_adversarial_debate")
        status = "healthy" if not findings else "degraded"
        return {"tick": tick, "status": status, "findings": findings, "active_agents": len(active), "evidence": evidence_count, "debates": debate_count}

    def command_snapshot(self, tick: int, diagnostics: dict, collective: dict, generation: int | None = None) -> dict:
        return {
            "tick": tick,
            "constitution": dict(self.CONSTITUTION),
            "diagnostics": diagnostics,
            "collective_learning": collective,
            "generation": generation,
            "replay_log": str(self.replay_path),
            "genealogy_log": str(self.genealogy_path),
            "experiment_log": str(self.experiments_path),
        }

    def replay(self, limit: int = 100) -> list[dict]:
        if not self.replay_path.exists():
            return []
        lines = self.replay_path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines[-max(1, min(limit, 1000)):]]


__all__ = ["EvolutionFrontier", "FrontierEvent"]
