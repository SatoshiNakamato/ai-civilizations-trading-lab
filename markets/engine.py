from __future__ import annotations

from random import Random

from .council_runner import CouncilRunner
from .validation import ValidationLab


class MarketEngine:
    """Runs market research, candidate discovery and paper validation together."""

    def __init__(self, seed: int = 42):
        self.rng = Random(seed)
        self.council_runner = CouncilRunner(seed=seed)
        self.validation = ValidationLab()
        self.tick = 0

    def step(self, agent_ids: list[str]) -> dict:
        self.tick += 1
        council = self.council_runner.run_generation(agent_ids)
        ranked = council["top"]
        for candidate in ranked[:10]:
            # Synthetic return path for validation only. This deliberately
            # represents noisy out-of-sample testing, not a trading signal.
            quality = candidate["score"] - candidate["failures"] * 0.03
            returns = [quality + self.rng.uniform(-0.2, 0.2) for _ in range(20)]
            self.validation.evaluate(candidate["thesis"], returns)
        return {"tick": self.tick, "council": council, "validation": self.validation.snapshot()}
