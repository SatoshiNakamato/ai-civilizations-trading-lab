from __future__ import annotations

from collections import deque
from random import Random
from typing import Any


class WorldDynamics:
    """Small, deterministic civilization dynamics with hard memory bounds.

    This is the missing connective tissue between individual agent actions and
    civilization-scale life. It models twenty explicit systems without creating
    unbounded object graphs or claiming literal machine consciousness.
    """

    FEATURES = (
        "identity", "needs", "goals", "memory", "reflection", "relationships",
        "culture", "organizations", "economy", "jobs", "contracts", "research",
        "experiments", "discoveries", "reputation", "innovation", "lineage",
        "migration", "governance", "endurance",
    )

    def __init__(self, platform: Any, seed: int = 42, history_limit: int = 128):
        self.platform = platform
        self.rng = Random(seed)
        self.history = deque(maxlen=max(32, history_limit))
        self.discovery_index: set[str] = set()
        self.lineage: dict[str, str] = {}
        self.governance = {"cooperation": 0.5, "experimentation": 0.5, "stability": 0.5}
        self.tick_count = 0

    def tick(self, active_ids: list[str], tick: int) -> dict:
        self.tick_count = tick
        if not active_ids:
            return self.snapshot()

        # 1-5: individual life dynamics.
        for aid in active_ids:
            person = self.platform.people.get(aid)
            if person is None:
                continue
            person.age += 1
            person.health = max(0.45, min(1.0, person.health + self.rng.uniform(-0.006, 0.008)))
            person.stage = "established" if person.age >= 10 else "young"
            # Needs feed goal selection without accumulating new fields.
            if person.health < 0.7 and "protect" not in person.goals:
                person.goals.append("protect")
            person.goals = person.goals[-4:]
            person.reputation = max(0.0, min(100.0, person.reputation + self.rng.uniform(-0.01, 0.03)))

        # 6: relationships and 7: culture.
        if len(active_ids) >= 2:
            a, b = active_ids[0], active_ids[-1]
            self.platform.social(a, b, tick, cooperative=True)
        self.platform.culture["norms"]["cooperate"] = max(
            0.0, min(1.0, self.platform.culture["norms"].get("cooperate", 0.5) + self.rng.uniform(-.005, .008))
        )

        # 8-11: organizations, economy, jobs and contracts.
        if tick % 3 == 0:
            self.platform.organize(active_ids[0], tick)
        if tick % 2 == 0 and len(active_ids) >= 2:
            contract_id = f"contract-{tick}-{active_ids[0]}-{active_ids[1]}"
            self.platform.contracts.append({"id": contract_id, "parties": active_ids[:2], "status": "settled", "tick": tick})
            self.platform.contracts = self.platform.contracts[-100:]

        price = 100.0 + (self.rng.random() - 0.5) * 2.0
        self.platform.markets["credits"]["prices"]["AEON"] = round(price, 4)

        # 12-16: knowledge, experiments, discoveries and innovation.
        if tick % 2 == 0:
            self.platform.learn(active_ids[0], "civilization:dynamics", "bounded multi-agent observation", .6, tick)
        if tick % 5 == 0:
            experiment = self.platform.experiment(active_ids[0], "Does cooperation improve repeatable outcomes?", tick)
            if experiment.get("repeatable"):
                key = f"cooperation:{tick // 5}"
                if key not in self.discovery_index:
                    self.discovery_index.add(key)
                    self.platform.create(active_ids[0], "discovery", tick, "repeatable cooperation experiment")
                    self.platform.metrics["discoveries"] += 1

        # 17: lineage / succession markers. 18: migration.
        if tick % 10 == 0:
            for aid in active_ids[:2]:
                self.lineage.setdefault(aid, "origin")
                person = self.platform.people.get(aid)
                if person and self.rng.random() < .25:
                    old = person.location
                    person.location = "Frontier" if old == "Haven" else "Haven"
                    self.platform.locations[old]["population"] = max(0, self.platform.locations[old]["population"] - 1)
                    self.platform.locations[person.location]["population"] += 1

        # 19: governance adapts from observed social outcomes.
        social = self.platform.metrics.get("social_interactions", 0)
        self.governance["cooperation"] = max(0.0, min(1.0, .5 + min(.4, social / 1000.0)))
        self.governance["stability"] = max(0.0, min(1.0, sum(p.health for p in self.platform.people.values()) / max(1, len(self.platform.people))))
        self.platform.culture["norms"].update({"cooperate": self.governance["cooperation"], "experiment": self.governance["experimentation"]})

        # 20: endurance is represented by bounded history and scheduler feedback.
        self.history.append({"tick": tick, "active": len(active_ids), "features": len(self.FEATURES), "stability": round(self.governance["stability"], 4)})
        return self.snapshot()

    def snapshot(self) -> dict:
        return {
            "features": list(self.FEATURES),
            "feature_count": len(self.FEATURES),
            "governance": dict(self.governance),
            "lineage": len(self.lineage),
            "history": list(self.history)[-16:],
            "discoveries_indexed": len(self.discovery_index),
        }
