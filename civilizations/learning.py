from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class LearningEvent:
    category: str
    success: float
    difficulty: float
    novelty: float
    description: str


@dataclass
class Intelligence:
    """Internal capability model; not a real IQ measurement."""
    reasoning: float = 100.0
    creativity: float = 100.0
    research: float = 100.0
    market_skill: float = 100.0
    risk_awareness: float = 100.0
    prediction_skill: float = 100.0
    communication: float = 100.0
    skepticism: float = 100.0
    learning_rate: float = 100.0
    experience: int = 0
    successful_research: int = 0
    failed_research: int = 0
    discoveries: int = 0
    validated_predictions: int = 0
    history: List[LearningEvent] = field(default_factory=list)

    @property
    def capability_score(self) -> float:
        values = [self.reasoning, self.creativity, self.research, self.market_skill,
                  self.risk_awareness, self.prediction_skill, self.communication,
                  self.skepticism, self.learning_rate]
        return sum(values) / len(values)

    def learn(self, category: str, success: float, difficulty: float,
              novelty: float, description: str) -> None:
        success = max(0.0, min(1.0, success))
        difficulty = max(0.0, min(1.0, difficulty))
        novelty = max(0.0, min(1.0, novelty))
        self.experience += 1
        self.history.append(LearningEvent(category, success, difficulty, novelty, description))
        self.history = self.history[-200:]

        change = 0.05 + 0.20 * success + 0.10 * difficulty + 0.10 * novelty
        change -= 0.08 * (1.0 - success)
        self._apply(category, change)

        if success >= 0.65:
            self.successful_research += 1
        else:
            self.failed_research += 1
        if success >= 0.80:
            self.discoveries += 1
        if category == "prediction" and success >= 0.70:
            self.validated_predictions += 1

    def _apply(self, category: str, change: float) -> None:
        mapping = {
            "reasoning": "reasoning", "creativity": "creativity", "research": "research",
            "market": "market_skill", "risk": "risk_awareness", "prediction": "prediction_skill",
            "communication": "communication", "skepticism": "skepticism", "learning": "learning_rate",
        }
        attribute = mapping.get(category, "reasoning")
        setattr(self, attribute, max(1.0, min(500.0, getattr(self, attribute) + change)))

    def learn_from_prediction(self, accuracy: float, difficulty: float = 0.5) -> None:
        self.learn("prediction", accuracy, difficulty, 0.5, "Validated prediction result")

    def learn_from_research(self, quality: float, difficulty: float = 0.5,
                            novelty: float = 0.5) -> None:
        self.learn("research", quality, difficulty, novelty, "Research experiment completed")

    def learn_from_trade_result(self, performance: float, risk_quality: float) -> None:
        self.learn("market", performance, 0.7, 0.4, "Simulated strategy result")
        self.learn("risk", risk_quality, 0.7, 0.3, "Risk-management result")

    def learn_from_collaboration(self, usefulness: float) -> None:
        self.learn("communication", usefulness, 0.4, 0.3, "Collaboration with another agent")

    def profile(self) -> dict:
        return {
            "capability_score": round(self.capability_score, 3),
            "reasoning": round(self.reasoning, 3),
            "creativity": round(self.creativity, 3),
            "research": round(self.research, 3),
            "market_skill": round(self.market_skill, 3),
            "risk_awareness": round(self.risk_awareness, 3),
            "prediction_skill": round(self.prediction_skill, 3),
            "communication": round(self.communication, 3),
            "skepticism": round(self.skepticism, 3),
            "learning_rate": round(self.learning_rate, 3),
            "experience": self.experience,
            "successful_research": self.successful_research,
            "failed_research": self.failed_research,
            "discoveries": self.discoveries,
            "validated_predictions": self.validated_predictions,
        }
