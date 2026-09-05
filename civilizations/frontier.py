from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from random import Random
from typing import Iterable


@dataclass
class FrontierSignal:
    signal_id: str
    source_civilization: str
    thesis: str
    confidence: float
    novelty: float
    contagion: float = 0.0
    challenged: bool = False
    adopted: bool = False


@dataclass
class CivilizationState:
    civilization_id: str
    doctrine: str
    capital: float = 1000.0
    knowledge: float = 0.0
    resilience: float = 0.5
    influence: float = 0.0
    generation: int = 0


class FrontierCivilizationEngine:
    """A bounded laboratory for multi-civilization emergence.

    The engine simulates the previously discussed 'impossible' ideas without
    giving agents uncontrolled network access, self-replication, or authority
    to move real funds. Memetic propagation is an in-lab state transition.
    """

    DOCTRINES = (
        "evidence-first",
        "adversarial-skeptic",
        "cooperative-alpha",
        "capital-preservation",
        "exploration",
        "prediction-calibration",
    )

    def __init__(self, seed: int = 42, civilization_count: int = 6, signal_limit: int = 1000):
        if civilization_count < 2:
            raise ValueError("civilization_count must be at least 2")
        self.rng = Random(seed)
        self.signal_limit = max(50, signal_limit)
        self.civilizations = {
            f"CIV-{i:03d}": CivilizationState(
                civilization_id=f"CIV-{i:03d}",
                doctrine=self.DOCTRINES[(i - 1) % len(self.DOCTRINES)],
                resilience=0.35 + self.rng.random() * 0.55,
            )
            for i in range(1, civilization_count + 1)
        }
        self.signals: dict[str, FrontierSignal] = {}
        self.events: list[dict] = []
        self.tick = 0
        self.championship: list[str] = []
        self._seed_signals()

    def _seed_signals(self) -> None:
        for civ in self.civilizations.values():
            self.emit_signal(civ.civilization_id, f"{civ.doctrine} doctrine", .5, .5)

    def emit_signal(self, civilization_id: str, thesis: str, confidence: float, novelty: float) -> FrontierSignal:
        if civilization_id not in self.civilizations:
            raise KeyError(civilization_id)
        digest = sha256(f"{civilization_id}:{self.tick}:{thesis}:{len(self.signals)}".encode()).hexdigest()[:16]
        signal = FrontierSignal(
            signal_id=f"SIG-{digest}",
            source_civilization=civilization_id,
            thesis=thesis[:500],
            confidence=max(0.0, min(1.0, confidence)),
            novelty=max(0.0, min(1.0, novelty)),
        )
        self.signals[signal.signal_id] = signal
        return signal

    def challenge(self, signal: FrontierSignal) -> bool:
        """Adversarially challenge a signal before it can propagate."""
        penalty = self.rng.random() * 0.35
        signal.challenged = True
        signal.confidence = max(0.0, signal.confidence - penalty)
        return signal.confidence >= 0.45 and signal.novelty >= 0.20

    def propagate(self, signal: FrontierSignal, target_civilization: str) -> bool:
        """Simulate bounded idea contagion between civilizations."""
        target = self.civilizations[target_civilization]
        if not signal.challenged or not self.challenge(signal):
            return False
        distance = 0.15 if target.civilization_id == signal.source_civilization else 0.0
        probability = max(0.0, min(0.92, signal.confidence * .55 + signal.novelty * .30 + target.resilience * .05 + distance))
        accepted = self.rng.random() < probability
        signal.contagion = probability
        signal.adopted = accepted
        if accepted:
            target.knowledge += signal.novelty * signal.confidence
            target.influence = min(1.0, target.influence + .01)
            self._event("idea_adopted", signal.source_civilization, target.civilization_id, signal.signal_id)
        else:
            target.resilience = min(1.0, target.resilience + .005)
            self._event("idea_rejected", signal.source_civilization, target.civilization_id, signal.signal_id)
        return accepted

    def economic_stress_test(self, shock: float = 0.25) -> dict[str, float]:
        """Apply a paper-only shock and score civilization resilience."""
        shock = max(0.0, min(1.0, shock))
        scores = {}
        for civ in self.civilizations.values():
            loss = civ.capital * shock * (1.0 - civ.resilience)
            civ.capital = max(0.0, civ.capital - loss)
            civ.knowledge += civ.resilience * shock
            scores[civ.civilization_id] = round(civ.capital * (.5 + civ.resilience) + civ.knowledge * 10, 4)
        self._event("economic_stress", "SYSTEM", "ALL", f"shock={shock:.3f}")
        return scores

    def championship_round(self) -> list[dict]:
        """Rank civilizations on resilience, knowledge and influence only."""
        ranking = sorted(
            self.civilizations.values(),
            key=lambda c: (c.knowledge * 10 + c.capital * .01 + c.resilience * 100 + c.influence * 50),
            reverse=True,
        )
        self.championship = [c.civilization_id for c in ranking]
        return [
            {
                "rank": i,
                "civilization_id": c.civilization_id,
                "doctrine": c.doctrine,
                "score": round(c.knowledge * 10 + c.capital * .01 + c.resilience * 100 + c.influence * 50, 4),
            }
            for i, c in enumerate(ranking, 1)
        ]

    def tick_once(self) -> dict:
        self.tick += 1
        for civ in self.civilizations.values():
            thesis = f"{civ.doctrine} mutation {self.tick}: seek a falsifiable edge"
            signal = self.emit_signal(civ.civilization_id, thesis, .45 + self.rng.random() * .5, self.rng.random())
            self.challenge(signal)
            targets = [x for x in self.civilizations if x != civ.civilization_id]
            if targets:
                self.propagate(signal, self.rng.choice(targets))
            civ.generation += 1
        self.economic_stress_test(.05)
        self.championship_round()
        self._trim()
        return self.snapshot()

    def _event(self, kind: str, actor: str, target: str, object_id: str) -> None:
        self.events.append({"tick": self.tick, "event": kind, "actor": actor, "target": target, "object": object_id})

    def _trim(self) -> None:
        if len(self.signals) > self.signal_limit:
            keep = sorted(self.signals.values(), key=lambda s: (s.adopted, s.confidence, s.novelty), reverse=True)[: self.signal_limit]
            self.signals = {s.signal_id: s for s in keep}
        self.events = self.events[-500:]

    def snapshot(self) -> dict:
        ranking = self.championship_round()
        return {
            "tick": self.tick,
            "civilizations": len(self.civilizations),
            "signals": len(self.signals),
            "adopted_signals": sum(s.adopted for s in self.signals.values()),
            "championship": ranking,
            "civilization_state": [asdict(c) for c in self.civilizations.values()],
            "recent_events": self.events[-30:],
            "safety": {
                "real_trading": False,
                "self_replication": False,
                "unbounded_network_propagation": False,
                "external_fund_movement": False,
            },
        }
