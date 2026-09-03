from __future__ import annotations

import random
from typing import Iterable

from .council import MarketResearchCouncil
from .intelligence import MarketIntelligence, VenueQuote


SPECIALTIES = ("arbitrage", "prediction", "macro", "quant", "risk", "research")


class CouncilRunner:
    """Deterministic simulation coordinator for agent market research."""

    def __init__(self, council: MarketResearchCouncil | None = None, seed: int = 42):
        self.council = council or MarketResearchCouncil(MarketIntelligence())
        self.rng = random.Random(seed)
        self.generation = 0

    def generate_market_snapshot(self, symbols: Iterable[str] = ("BTC", "ETH", "SOL")) -> None:
        quotes = []
        venues = ("VENUE_A", "VENUE_B", "VENUE_C")
        for symbol in symbols:
            base = self.rng.uniform(100, 100000)
            for venue in venues:
                mid = base * (1 + self.rng.uniform(-0.008, 0.008))
                spread = max(mid * 0.0005, 0.01)
                quotes.append(VenueQuote(venue, symbol, mid - spread, mid + spread, self.generation))
        self.council.market.ingest(quotes)

    def run_generation(self, agent_ids: Iterable[str]) -> dict:
        self.generation += 1
        self.council.generation = self.generation
        self.generate_market_snapshot()
        opportunities = self.council.market.scan_arbitrage()
        agents = list(agent_ids)
        for opportunity in opportunities[: min(20, len(opportunities))]:
            agent = self.rng.choice(agents) if agents else "SYSTEM"
            self.council.admit_arbitrage(agent, [opportunity])

        # Agents independently submit research hypotheses. Their initial score
        # is deliberately modest; validation, not a hard-coded IQ, determines growth.
        for agent in agents:
            specialty = SPECIALTIES[self.rng.randrange(len(SPECIALTIES))]
            thesis = f"{specialty} research hypothesis for generation {self.generation}"
            self.council.submit(agent, specialty, thesis, evidence=1, score=self.rng.uniform(0.25, 0.65))

        # Peer review: reviewers cannot review their own candidate.
        for index, candidate in enumerate(self.council.candidates[-max(1, len(agents)):]):
            if not agents:
                break
            reviewer = self.rng.choice([a for a in agents if a != candidate.agent_id] or agents)
            support = self.rng.random() > 0.35
            self.council.review(reviewer, len(self.council.candidates) - max(1, len(agents)) + index, support, self.rng.uniform(0.4, 0.95))

        return self.council.snapshot()
