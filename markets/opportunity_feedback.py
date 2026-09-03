from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Feedback:
    hypothesis: str
    observations: int
    successes: int
    failures: int
    confidence: float


class OpportunityFeedback:
    def __init__(self):
        self._data: dict[str, list[str]] = {}

    def observe(self, hypothesis: str, outcome: str) -> Feedback:
        bucket = self._data.setdefault(hypothesis, [])
        bucket.append(outcome)
        successes = sum(x == "success" for x in bucket)
        failures = sum(x == "failure" for x in bucket)
        n = len(bucket)
        confidence = successes / n if n else 0.0
        return Feedback(hypothesis, n, successes, failures, confidence)

    def snapshot(self) -> dict:
        return {k: {"observations": len(v), "successes": v.count("success"), "failures": v.count("failure")} for k, v in self._data.items()}
