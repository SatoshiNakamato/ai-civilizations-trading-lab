from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any


@dataclass
class Belief:
    statement: str
    confidence: float = 0.5
    evidence: int = 0
    successes: int = 0
    failures: int = 0


@dataclass
class CognitiveState:
    agent_id: str
    beliefs: dict[str, Belief] = field(default_factory=dict)
    questions: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    observations: int = 0


class CognitiveEngine:
    """A deterministic local reasoning layer.

    It does not claim consciousness. It maintains beliefs, questions and
    evidence-weighted updates so agents can keep learning even when no paid
    LLM API is available.
    """

    def __init__(self):
        self.states: dict[str, CognitiveState] = {}

    def state(self, agent_id: str) -> CognitiveState:
        return self.states.setdefault(agent_id, CognitiveState(agent_id))

    def observe(self, agent_id: str, observation: str, evidence: float = 0.5) -> None:
        state = self.state(agent_id)
        state.observations += 1
        state.lessons.append(f"observation:{observation[:240]} (evidence={max(0,min(1,evidence)):.2f})")
        state.lessons = state.lessons[-100:]

    def form_belief(self, agent_id: str, statement: str, confidence: float = 0.5) -> Belief:
        state = self.state(agent_id)
        key = statement.strip().lower()
        belief = state.beliefs.get(key)
        if belief is None:
            belief = Belief(statement, max(0,min(1,confidence)))
            state.beliefs[key] = belief
        else:
            belief.confidence = (belief.confidence + confidence) / 2
        return belief

    def update(self, agent_id: str, statement: str, success: bool, evidence_quality: float = 0.5) -> Belief:
        belief = self.form_belief(agent_id, statement)
        q = max(0.0, min(1.0, evidence_quality))
        belief.evidence += 1
        if success:
            belief.successes += 1
            belief.confidence += (1 - belief.confidence) * 0.12 * q
        else:
            belief.failures += 1
            belief.confidence -= belief.confidence * 0.12 * q
        belief.confidence = max(0.0, min(1.0, belief.confidence))
        return belief

    def ask(self, agent_id: str, question: str) -> None:
        state = self.state(agent_id)
        state.questions.append(question)
        state.questions = state.questions[-50:]

    def reason(self, agent_id: str, context: dict[str, Any]) -> dict[str, Any]:
        state = self.state(agent_id)
        trend = float(context.get("trend", 0.0))
        volatility = float(context.get("volatility", 0.0))
        if abs(trend) > max(0.002, volatility * 1.5):
            conclusion = "trend deserves further testing"
        elif volatility > 0.01:
            conclusion = "high uncertainty; prioritize risk analysis"
        else:
            conclusion = "signal is weak; seek more evidence"
        return {"agent_id": agent_id, "conclusion": conclusion, "confidence": min(1.0, 0.5 + abs(trend) * 5), "observations": state.observations}

    def snapshot(self) -> dict[str, Any]:
        return {"agents": len(self.states), "observations": sum(s.observations for s in self.states.values()), "beliefs": sum(len(s.beliefs) for s in self.states.values()), "timestamp": time()}
