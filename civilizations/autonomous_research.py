from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib, time
from civilizations.agent_brain import AgentBrain, ResearchHypothesis
from civilizations.market_research_feed import PublicMarketResearchFeed
from civilizations.signal_research import PublicSignalResearch

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
    """Public-signal research -> meme concept candidates -> launch candidates."""
    WATCHLIST = ("BTC", "ETH", "SOL", "DOGE", "PEPE", "BASE", "ARB", "OP")
    MEME_THEMES = ("VIRAL", "FROG", "CAT", "PEPE", "DOGE", "MOCHI", "BONGO", "PULSE")
    THESIS_TEMPLATES = (
        "momentum/relative-strength anomaly",
        "liquidity and volume regime shift",
        "cross-market price dislocation",
        "event-driven repricing hypothesis",
        "meme/social attention acceleration",
        "news-driven meme narrative emergence",
    )
    def __init__(self, brain=None, feed=None, signals=None):
        self.brain = brain or AgentBrain(); self.feed = feed or PublicMarketResearchFeed(); self.signals_feed = signals or PublicSignalResearch()
        self.history = []; self.last_market = []; self.last_signals = []
    def cycle(self, agents, cycle, *, limit=8):
        if not agents: return []
        self.last_market = self.feed.fetch(); market = {x.asset: x for x in self.last_market}
        self.last_signals = self.signals_feed.fetch()
        signal_text = " | ".join(s.title for s in self.last_signals[:5])
        signal_boost = min(0.14, len(self.last_signals) * 0.01)
        preferred = [a for a in ("A001", "A002", "A003", "A004") if a in agents]
        ordered = (preferred + [a for a in agents if a not in preferred])[:limit]
        candidates = []
        for i, agent in enumerate(ordered):
            ticker = self.WATCHLIST[(cycle * 3 + i) % len(self.WATCHLIST)]
            template = self.THESIS_TEMPLATES[i % len(self.THESIS_TEMPLATES)]
            theme = self.MEME_THEMES[(cycle + i) % len(self.MEME_THEMES)]
            digest = hashlib.sha256(f"{cycle}:{agent}:{ticker}:{template}:{signal_text}".encode()).digest()
            obs = market.get(ticker); move = obs.change_24h if obs else 0.0
            evidence = min(0.99, 0.78 + digest[0] / 2550 + min(0.08, abs(move) / 1000) + signal_boost)
            executionability = min(0.98, 0.76 + digest[1] / 1275 + signal_boost / 2)
            risk = min(0.35, 0.10 + digest[2] / 1275)
            thesis = f"{template} for meme concept {theme}; public 24h move={move:.3f}%; signals={signal_text[:300] or 'no fresh social/news feed'}; validate liquidity, narrative durability, catalyst and invalidation conditions."
            h = self.brain.generate(agent, ticker, thesis, evidence=evidence, executionability=executionability, risk=risk, consensus_score=0.22 + digest[3] / 510)
            d = self._debate(h, digest); ev = min(1.0, h.evidence * .7 + d.survival_score * .3)
            rank = h.score * .55 + ev * .30 + d.survival_score * .15
            candidates.append(Opportunity(h, d, ev, rank, rank * (1 - h.risk)))
        candidates.sort(key=lambda x: x.risk_adjusted, reverse=True); self.history.extend(candidates[:3]); self.history = self.history[-50:]
        return candidates
    def _debate(self, h, digest):
        supporters, challengers = 3 + digest[4] % 7, 2 + digest[5] % 8
        objections = ("liquidity may be insufficient", "signal may be regime-dependent", "meme attention may decay", "catalyst timing is uncertain")
        survival = max(0.0, min(1.0, h.score * .75 + (1 - challengers / (supporters + challengers)) * .25))
        return DebateResult(h.hypothesis_id, supporters, challengers, objections[:1 + digest[6] % len(objections)], survival)
    def snapshot(self):
        return {"market_observations": [asdict(x) for x in self.last_market], "public_signals": [asdict(x) for x in self.last_signals], "history": [{"hypothesis": asdict(x.hypothesis), "debate": asdict(x.debate), "evidence_score": x.evidence_score, "rank_score": x.rank_score, "risk_adjusted": x.risk_adjusted} for x in self.history[-10:]], "updated_at": time.time()}
