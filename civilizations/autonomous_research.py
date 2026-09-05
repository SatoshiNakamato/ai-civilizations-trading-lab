from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib, time
from civilizations.agent_brain import AgentBrain, ResearchHypothesis
from civilizations.market_research_feed import PublicMarketResearchFeed, MarketObservation

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
    """Run a full civilization research pass, then return the strongest candidates."""
    WATCHLIST = ("BTC", "ETH", "SOL", "DOGE", "PEPE", "BASE", "ARB", "OP")
    THESIS_TEMPLATES = (
        "momentum/relative-strength anomaly",
        "liquidity and volume regime shift",
        "cross-market price dislocation",
        "event-driven repricing hypothesis",
    )
    def __init__(self, brain=None, feed=None):
        self.brain = brain or AgentBrain(); self.feed = feed or PublicMarketResearchFeed()
        self.history = []; self.last_market = []
    def cycle(self, agents, cycle, *, limit=8):
        if not agents: return []
        self.last_market = self.feed.fetch(); market = {x.asset: x for x in self.last_market}
        # Every configured civilization gets a research/debate pass. `limit`
        # controls how many survivors are handed to execution/risk stages, not
        # how many agents participate in research.
        ordered = list(agents)
        preferred = [a for a in ("A001", "A002", "A003", "A004") if a in ordered]
        ordered = preferred + [a for a in ordered if a not in preferred]
        candidates = []
        for i, agent in enumerate(ordered):
            ticker = self.WATCHLIST[(cycle * 3 + i) % len(self.WATCHLIST)]
            template = self.THESIS_TEMPLATES[i % len(self.THESIS_TEMPLATES)]
            digest = hashlib.sha256(f"{cycle}:{agent}:{ticker}:{template}".encode()).digest()
            obs = market.get(ticker); move = obs.change_24h if obs else 0.0
            evidence = min(0.99, 0.80 + digest[0] / 2550 + min(0.08, abs(move) / 1000))
            executionability = min(0.98, 0.74 + digest[1] / 1275)
            risk = min(0.35, 0.10 + digest[2] / 1275)
            h = self.brain.generate(agent, ticker, f"{template} detected for {ticker}; public 24h move={move:.3f}%; test liquidity, momentum, catalysts and invalidation conditions.", evidence=evidence, executionability=executionability, risk=risk, consensus_score=0.20 + digest[3] / 510)
            d = self._debate(h, digest); ev = min(1.0, h.evidence * .7 + d.survival_score * .3)
            rank = h.score * .55 + ev * .30 + d.survival_score * .15
            candidates.append(Opportunity(h, d, ev, rank, rank * (1 - h.risk)))
        candidates.sort(key=lambda x: x.risk_adjusted, reverse=True)
        survivors = candidates[:max(1, limit)]
        self.history.extend(survivors); self.history = self.history[-100:]
        return survivors
    def _debate(self, h, digest):
        supporters, challengers = 3 + digest[4] % 7, 2 + digest[5] % 8
        objections = ("liquidity may be insufficient", "signal may be regime-dependent", "catalyst timing is uncertain")
        survival = max(0.0, min(1.0, h.score * .75 + (1 - challengers / (supporters + challengers)) * .25))
        return DebateResult(h.hypothesis_id, supporters, challengers, objections[:1 + digest[6] % 3], survival)
    def snapshot(self):
        return {"market_observations": [asdict(x) for x in self.last_market], "history": [{"hypothesis": asdict(x.hypothesis), "debate": asdict(x.debate), "evidence_score": x.evidence_score, "rank_score": x.rank_score, "risk_adjusted": x.risk_adjusted} for x in self.history[-10:]], "updated_at": time.time()}
