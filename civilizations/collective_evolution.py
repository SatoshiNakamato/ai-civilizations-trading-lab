"""Governed fifteen-stage collective evolution orchestration.

The loop composes the existing communication, research, experiment, frontier,
and governor primitives. It deliberately stops at governed mutation proposals:
agents may generate evidence, debate, experiments, and proposals, but they do
not receive arbitrary source-code, credential, or deployment authority.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Mapping, Sequence, Any

from .agent_communication import AgentCommunicationBus
from .learning_communication import CollectiveLearning
from .evolution_frontier import EvolutionFrontier


@dataclass(frozen=True, slots=True)
class EvolutionStage:
    number: int
    name: str
    status: str
    details: dict[str, Any]


class CollectiveEvolutionLoop:
    """Execute one bounded research-to-evolution cycle across a population."""

    STAGES = (
        "observe",
        "assign_lanes",
        "independent_research",
        "peer_exchange",
        "synthesize",
        "generate_hypotheses",
        "adversarial_debate",
        "verify_evidence",
        "calibrate_confidence",
        "select_adoptions",
        "run_experiments",
        "evaluate_outcomes",
        "adapt_strategies",
        "record_genealogy",
        "propose_governed_mutation",
    )

    def __init__(self, bus: AgentCommunicationBus, collective: CollectiveLearning, frontier: EvolutionFrontier, platform=None):
        self.bus = bus
        self.collective = collective
        self.frontier = frontier
        self.platform = platform
        self.history: list[dict[str, Any]] = []

    @staticmethod
    def _unique(agents: Sequence[str]) -> list[str]:
        return list(dict.fromkeys(agents))

    def run(self, agents: Sequence[str], *, tick: int, evidence: Mapping[str, str], active_ids: Sequence[str] | None = None) -> dict[str, Any]:
        agents = self._unique(agents)
        active = self._unique(active_ids or agents)
        stages: list[EvolutionStage] = []

        # 1. Observe: normalize the evidence entering this cycle.
        usable = {aid: str(evidence.get(aid, "")).strip() for aid in agents}
        usable_count = sum(bool(v) for v in usable.values())
        stages.append(EvolutionStage(1, "observe", "complete", {"agents": len(agents), "evidence": usable_count}))

        # 2. Assign research lanes without changing agent credentials.
        lanes = {aid: ("research" if i % 3 == 0 else "challenge" if i % 3 == 1 else "experiment") for i, aid in enumerate(agents)}
        stages.append(EvolutionStage(2, "assign_lanes", "complete", {"lanes": lanes}))

        # 3. Independent research is represented by each agent's own evidence.
        independent = {aid: text for aid, text in usable.items() if text}
        stages.append(EvolutionStage(3, "independent_research", "complete", {"contributors": len(independent)}))

        # 4-10. Existing governed communication/learning machinery handles exchange,
        # synthesis, debate, scoring and adoption. No raw filesystem or API access.
        exchanges = self.collective.round(agents, tick=tick, evidence=usable)
        stages.append(EvolutionStage(4, "peer_exchange", "complete", {"exchanges": len(exchanges)}))
        synthesis = dict(self.collective.snapshot().get("last_synthesis", {}))
        stages.append(EvolutionStage(5, "synthesize", "complete", synthesis))

        hypotheses = []
        for item in exchanges:
            hypotheses.append({
                "agent": item.recipient,
                "source": item.sender,
                "hypothesis": f"Test whether {item.topic} evidence improves the recipient's prior strategy.",
                "evidence": item.evidence[:300],
                "confidence": item.confidence,
            })
        stages.append(EvolutionStage(6, "generate_hypotheses", "complete", {"hypotheses": len(hypotheses)}))

        debates = self.collective.debate(agents, tick=tick, topic="collective research review")
        stages.append(EvolutionStage(7, "adversarial_debate", "complete", {"debates": len(debates)}))

        verified = [h for h in hypotheses if h["evidence"] and h["confidence"] >= 0.5]
        stages.append(EvolutionStage(8, "verify_evidence", "complete", {"verified": len(verified), "rejected": len(hypotheses) - len(verified)}))

        mean_confidence = sum(h["confidence"] for h in verified) / max(1, len(verified))
        calibrated = round(max(0.0, min(1.0, mean_confidence * (0.9 if debates else 0.75))), 4)
        stages.append(EvolutionStage(9, "calibrate_confidence", "complete", {"confidence": calibrated, "debate_penalty": bool(debates)}))

        adoption = []
        for item in self.collective.snapshot().get("last_adoption", []):
            if item.get("adopted") and item.get("agent") in agents:
                adoption.append(item)
        stages.append(EvolutionStage(10, "select_adoptions", "complete", {"adopted": len(adoption), "candidates": len(verified)}))

        experiments = []
        if self.platform is not None:
            for item in adoption[: max(1, min(8, len(active)))] if adoption else []:
                aid = item["agent"]
                if aid not in active:
                    continue
                result = self.platform.experiment(aid, f"adopted:{item['source']}", tick)
                experiments.append(result)
        stages.append(EvolutionStage(11, "run_experiments", "complete", {"experiments": len(experiments)}))

        outcomes = [{"agent": r.get("agent"), "score": float(r.get("score", 0.0)), "repeatable": bool(r.get("repeatable"))} for r in experiments]
        mean_outcome = round(sum(x["score"] for x in outcomes) / max(1, len(outcomes)), 4)
        stages.append(EvolutionStage(12, "evaluate_outcomes", "complete", {"mean_score": mean_outcome, "repeatable": sum(x["repeatable"] for x in outcomes)}))

        # 13. Feed outcomes back as knowledge; this is strategy adaptation at the
        # simulation layer, not an automatic live-trading deployment.
        adaptations = 0
        if self.platform is not None:
            for outcome in outcomes:
                aid = outcome["agent"]
                self.platform.learn(aid, "strategy_feedback", f"experiment_score={outcome['score']:.4f}", outcome["score"], tick)
                adaptations += 1
        stages.append(EvolutionStage(13, "adapt_strategies", "complete", {"adaptations": adaptations}))

        # 14. Record parentage of adopted knowledge.
        genealogy = []
        for item in adoption:
            genealogy.append({"agent": item["agent"], "parent": item["source"], "reason": "knowledge adoption"})
            self.frontier.record_genealogy(tick, item["agent"], [item["source"]], "knowledge adoption")
        stages.append(EvolutionStage(14, "record_genealogy", "complete", {"records": len(genealogy)}))

        # 15. Produce a governed mutation proposal. The governor, not an agent,
        # controls whether source changes can ever leave the proposal state.
        proposals = 0
        if tick % 5 == 0 and adoption:
            lead = adoption[0]
            patch = (
                "# governed mutation proposal\n"
                f"# tick: {tick}\n# source-agent: {lead['source']}\n"
                f"# recipient-agent: {lead['agent']}\n# score: {lead['score']:.4f}\n"
            )
            self.frontier.propose_mutation(
                tick,
                lead["agent"],
                f"collective-{lead['source']}-to-{lead['agent']}",
                "Generated after exchange, adversarial review, verification, adoption and experiment feedback.",
                patch,
            )
            proposals = 1
        stages.append(EvolutionStage(15, "propose_governed_mutation", "complete", {"proposals": proposals, "source_write": False}))

        cycle = {
            "tick": tick,
            "agents": len(agents),
            "active_agents": len(active),
            "stages": [asdict(stage) for stage in stages],
            "complete": len(stages) == 15 and all(stage.status == "complete" for stage in stages),
            "research_exchanges": len(exchanges),
            "debates": len(debates),
            "adoptions": len(adoption),
            "experiments": len(experiments),
            "mean_confidence": calibrated,
            "mean_experiment_score": mean_outcome,
            "genealogy_records": len(genealogy),
            "mutation_proposals": proposals,
        }
        self.history.append(cycle)
        self.history = self.history[-100:]
        return cycle

    def snapshot(self) -> dict[str, Any]:
        return {"stage_count": 15, "stage_names": list(self.STAGES), "history": list(self.history[-100:])}


__all__ = ["CollectiveEvolutionLoop", "EvolutionStage"]
