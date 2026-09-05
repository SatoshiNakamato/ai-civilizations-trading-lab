from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Dict, List


@dataclass
class Memory:
    tick: int
    kind: str
    text: str
    importance: float = 0.5


@dataclass
class Relationship:
    trust: float = 0.0
    bond: float = 0.0
    conflict: float = 0.0
    interactions: int = 0


@dataclass
class LifeState:
    energy: float = 1.0
    curiosity: float = 0.5
    belonging: float = 0.5
    security: float = 0.5
    achievement: float = 0.5
    wellbeing: float = 0.75


class LifeEngine:
    """Persistent life layer for simulated beings.

    This models continuity, needs, relationships, reflection and identity.
    It does not claim biological or subjective consciousness; it supplies the
    persistent architecture needed for agents to behave as continuing selves.
    """

    def __init__(self, seed: int = 42, memory_limit: int = 80):
        self.rng = Random(seed)
        self.memory_limit = memory_limit
        self.memories: Dict[str, List[Memory]] = {}
        self.relationships: Dict[str, Dict[str, Relationship]] = {}
        self.states: Dict[str, LifeState] = {}
        self.self_models: Dict[str, Dict[str, object]] = {}
        self.legacies: Dict[str, List[str]] = {}

    def register(self, agent_id: str, values: List[str] | None = None) -> None:
        self.memories.setdefault(agent_id, [])
        self.relationships.setdefault(agent_id, {})
        self.states.setdefault(agent_id, LifeState())
        self.self_models.setdefault(agent_id, {
            "identity": agent_id,
            "values": list(values or ["curiosity", "survival", "growth"]),
            "beliefs_changed": 0,
            "reflections": 0,
            "life_stage": "young",
            "purpose": "discover and improve",
        })
        self.legacies.setdefault(agent_id, [])

    def remember(self, agent_id: str, tick: int, text: str, kind: str = "experience", importance: float = 0.5) -> None:
        self.register(agent_id)
        self.memories[agent_id].append(Memory(tick, kind, text[:500], max(0.0, min(1.0, importance))))
        self.memories[agent_id] = sorted(self.memories[agent_id], key=lambda m: (m.importance, m.tick), reverse=True)[: self.memory_limit]

    def interact(self, a: str, b: str, tick: int, outcome: float) -> None:
        self.register(a); self.register(b)
        for left, right in ((a, b), (b, a)):
            rel = self.relationships[left].setdefault(right, Relationship())
            rel.interactions += 1
            if outcome >= 0:
                rel.trust = min(1.0, rel.trust + 0.03 * outcome)
                rel.bond = min(1.0, rel.bond + 0.02 * outcome)
            else:
                rel.conflict = min(1.0, rel.conflict + 0.04 * abs(outcome))
            self.remember(left, tick, f"Interaction with {right}: outcome={outcome:.3f}", "relationship", 0.45)

    def experience(self, agent_id: str, tick: int, success: float, novelty: float = 0.5) -> None:
        self.register(agent_id)
        s = self.states[agent_id]
        s.energy = max(0.0, min(1.0, s.energy + 0.05 * success - 0.03))
        s.curiosity = max(0.0, min(1.0, s.curiosity + 0.04 * novelty - 0.01 * success))
        s.achievement = max(0.0, min(1.0, s.achievement + 0.04 * success))
        s.wellbeing = max(0.0, min(1.0, 0.45 * s.energy + 0.35 * s.belonging + 0.20 * s.achievement))
        self.remember(agent_id, tick, f"Outcome={success:.3f}; novelty={novelty:.3f}", "experience", min(1.0, 0.4 + novelty * 0.4))

    def reflect(self, agent_id: str, tick: int) -> str:
        self.register(agent_id)
        memories = self.memories[agent_id][-8:]
        if not memories:
            reflection = "I have little history yet; I should explore before forming strong beliefs."
        else:
            avg = sum(m.importance for m in memories) / len(memories)
            reflection = f"I have {len(memories)} recent experiences; their average importance is {avg:.2f}. I should adapt my next actions to what repeatedly worked and failed."
        model = self.self_models[agent_id]
        model["reflections"] = int(model["reflections"]) + 1
        if int(model["reflections"]) > 5:
            model["life_stage"] = "established"
        self.remember(agent_id, tick, reflection, "reflection", 0.8)
        return reflection

    def teach(self, parent: str, child: str, tick: int) -> List[str]:
        self.register(parent); self.register(child)
        lessons = [m.text for m in self.memories[parent] if m.kind in {"reflection", "discovery"}][:5]
        for lesson in lessons:
            self.remember(child, tick, f"Inherited lesson from {parent}: {lesson}", "inheritance", 0.6)
        self.legacies[parent].append(child)
        return lessons

    def snapshot(self, agent_ids: List[str] | None = None) -> dict:
        ids = agent_ids or list(self.states)
        return {
            "beings": len(ids),
            "memories": sum(len(self.memories.get(i, [])) for i in ids),
            "relationships": sum(len(self.relationships.get(i, {})) for i in ids),
            "reflections": sum(int(self.self_models.get(i, {}).get("reflections", 0)) for i in ids),
            "life_stages": {stage: sum(1 for i in ids if self.self_models.get(i, {}).get("life_stage") == stage) for stage in {"young", "established"}},
        }
