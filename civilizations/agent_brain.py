from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
import math
import time
from pathlib import Path


@dataclass
class ResearchHypothesis:
    agent: str
    hypothesis_id: str
    ticker: str
    thesis: str
    novelty: float
    evidence: float
    executionability: float
    risk: float
    score: float
    created_at: float


class AgentBrain:
    """Deterministic research layer for auditable out-of-the-box hypotheses.

    It does not invent market facts: evidence must be supplied by upstream feeds.
    Novelty rewards disagreement with the current consensus, while risk and
    executionability prevent novelty from becoming an excuse for reckless action.
    """

    def __init__(self, audit_path="data/agent_hypotheses.jsonl"):
        self.audit_path = Path(audit_path)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    def generate(self, agent: str, ticker: str, thesis: str, *, evidence: float,
                 executionability: float, risk: float, consensus_score: float = 0.5):
        evidence = max(0.0, min(1.0, float(evidence)))
        executionability = max(0.0, min(1.0, float(executionability)))
        risk = max(0.0, min(1.0, float(risk)))
        consensus_score = max(0.0, min(1.0, float(consensus_score)))
        novelty = min(1.0, abs(consensus_score - 0.5) * 2.0 + 0.25)
        score = (0.30 * evidence + 0.25 * novelty + 0.25 * executionability + 0.20 * (1.0 - risk))
        raw = f"{agent.upper()}|{ticker.upper()}|{thesis}|{time.time_ns()}".encode()
        hypothesis_id = hashlib.sha256(raw).hexdigest()[:16]
        result = ResearchHypothesis(agent.upper(), hypothesis_id, ticker.upper(), thesis[:1000],
                                    novelty, evidence, executionability, risk, score, time.time())
        self._audit(result)
        return result

    def _audit(self, result):
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(result), sort_keys=True) + "\n")
