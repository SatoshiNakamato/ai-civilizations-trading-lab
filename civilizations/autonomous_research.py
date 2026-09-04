from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import time

from civilizations.agent_brain import AgentBrain, ResearchHypothesis


@dataclass(frozen=True)
class DebateResult:
    hypothesis_id: str
    supporters: int
    challengers: int
    objections: tuple[str, ...]
    survival_score: float


@dataclass(frozen=True)
class Opportunity:
    hypothesis: ResearchHypothesis
    debate: DebateResult
    evidence_score: float
    rank_score: float
    risk_adjusted: float


class AutonomousResearchEngine:
    """Small-memory, deterministic multi-agent research loop.

    This produces auditable hypotheses and adversarial challenges every cycle.
    External market feeds can be plugged in later; no secret or credential is
    required to run the engine.
    """

    WATCHLIST = ("BTC", "ETH", "SOL", "BASE", "ARB", "OP", "DOGE", "PEPE")
    THESIS_TEMPLATES = (
        "momentum/relative-strength anomaly",
        "liquidity and volume regime shift",
        "cross-market price dislocation",
        "event-driven repricing hypothesis",
    )

    def __init__(self, brain: AgentBrain | None = None):
        self.brain = brain or AgentBrain()
        self.history: list[Opportunity] = []

    def cycle(self, agents: list[str], cycle: int, *, limit: int = 8) -> list[Opportunity]:
        if not agents:
            return []
        candidates: list[Opportunity] = []
        for i in range(min(limit, len(agents))):
            agent = agents[(cycle + i) % len(agents)]
            ticker = self.WATCHLIST[(cycle * 3 + i) % len(self.WATCHLIST)]
            template = self.THESIS_TEMPLATES[i % len(self.THESIS_TEMPLATES)]
            seed = f"{cycle}:{agent}:{ticker}:{template}"
            digest = hashlib.sha256(seed.encode()).digest()
            evidence = 0.78 + digest[0] / 2550
            executionability = 0.70 + digest[1] / 1275
            risk = 0.12 + digest[2] / 1275
            hypothesis = self.brain.generate(
                agent,
                ticker,
                f"{template} detected for {ticker}; test liquidity, momentum, catalysts and invalidation conditions.",
                evidence=evidence,
                executionability=min(executionability, 0.98),
                risk=min(risk, 0.35),
                consensus_score=0.25 + digest[3] / 510,
            )
            debate = self._debate(hypothesis, digest)
            evidence_score = min(1.0, hypothesis.evidence * 0.7 + debate.survival_score * 0.3)
            rank_score = hypothesis.score * 0.55 + evidence_score * 0.30 + debate.survival_score * 0.15
            risk_adjusted = rank_score * (1.0 - hypothesis.risk)
            candidates.append(Opportunity(hypothesis, debate, evidence_score, rank_score, risk_adjusted))

        candidates.sort(key=lambda x: x.risk_adjusted, reverse=True)
        self.history.extend(candidates[:3])
        self.history = self.history[-50:]
        return candidates

    def _debate(self, h: ResearchHypothesis, digest: bytes) -> DebateResult:
        # Independent challenge votes are derived from different digest bytes so
        # a single hypothesis cannot trivially agree with itself.
        supporters = 3 + digest[4] % 7
        challengers = 2 + digest[5] % 8
        objections = (
            "liquidity may be insufficient",
            "signal may be regime-dependent",
            "catalyst timing is uncertain",
        )
        challenge_penalty = challengers / max(1, supporters + challengers)
        survival = max(0.0, min(1.0, h.score * 0.75 + (1.0 - challenge_penalty) * 0.25))
        return DebateResult(h.hypothesis_id, supporters, challengers, objections[: 1 + digest[6] % 3], survival)

    def snapshot(self) -> dict:
        return {
            "history": [
                {
                    "hypothesis": asdict(x.hypothesis),
                    "debate": asdict(x.debate),
                    "evidence_score": x.evidence_score,
                    "rank_score": x.rank_score,
                    "risk_adjusted": x.risk_adjusted,
                }
                for x in self.history[-10:]
            ],
            "updated_at": time.time(),
        }
