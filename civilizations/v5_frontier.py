"""V5 frontier capability registry and release gate.

The project already contains the individual building blocks for the 12 planned
V5 capabilities. This module does not duplicate them; it gives the release
process one governed, machine-readable contract that checks whether each
capability is represented by the expected code/docs/tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class V5Capability:
    number: int
    name: str
    evidence: tuple[str, ...]
    description: str


V5_CAPABILITIES: tuple[V5Capability, ...] = (
    V5Capability(1, "Release notes and changelog", ("RELEASE_NOTES.md", "CHANGELOG.md"), "Documented release surface."),
    V5Capability(2, "Architecture contract", ("ARCHITECTURE.md",), "System architecture is explicitly documented."),
    V5Capability(3, "Configuration reference", ("providers.example.env", "docs/LIVE_TRADING_SETUP.md"), "Operational configuration has a reproducible reference."),
    V5Capability(4, "Agent registry", ("civilizations/identity.py", "civilizations/generation.py", "civilizations/lineage.py"), "Agents have identity, generation, and lineage primitives."),
    V5Capability(5, "Live operations dashboard", ("web/app.py", "web/monitoring.py", "markets/live_monitor.py"), "Runtime state can be surfaced through the monitoring layer."),
    V5Capability(6, "Persistent event and audit history", ("civilizations/audit.py", "civilizations/evolution_governor.py", "markets/audit_log.py"), "Governed writes and market events leave durable audit evidence."),
    V5Capability(7, "Failure recovery and duplicate-deployment avoidance", ("civilizations/endurance.py", "markets/opportunity_lifecycle.py", "markets/deployment_policy.py"), "Resilience and lifecycle policy guard repeated actions."),
    V5Capability(8, "Kill switch and deployment pause", ("markets/deployment_policy.py", "civilizations/notification_governor.py"), "Deployment and notification paths are policy-gated."),
    V5Capability(9, "Bankr deployment ledger", ("markets/bankr_token_agent.py", "markets/observation_ledger.py", "docs/AUTONOMOUS_BANKR.md"), "Bankr-facing deployment state is isolated behind explicit ledger/policy code."),
    V5Capability(10, "On-chain observation", ("markets/onchain_activity.py", "markets/chain_data.py", "markets/observation_ledger.py"), "Public chain activity is observable without autonomous launch authority."),
    V5Capability(11, "Strategy leaderboard", ("markets/trader_leaderboard.py", "markets/strategy_metrics.py", "civilizations/fitness.py"), "Strategies can be scored and ranked."),
    V5Capability(12, "Strategy evolution", ("civilizations/strategy_evolution.py", "civilizations/arena_evolution.py", "civilizations/evolution_governor.py"), "Winning strategies can generate governed evolution proposals."),
)


class V5Frontier:
    """Read-only release gate for the twelve V5 capabilities."""

    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root).resolve()

    def check(self) -> dict[str, object]:
        results = []
        for capability in V5_CAPABILITIES:
            missing = [p for p in capability.evidence if not (self.root / p).exists()]
            results.append({
                "number": capability.number,
                "name": capability.name,
                "ok": not missing,
                "missing": missing,
            })
        return {
            "version": "5",
            "capabilities": results,
            "complete": all(item["ok"] for item in results),
        }

    def assert_ready(self) -> None:
        report = self.check()
        if not report["complete"]:
            missing = [f"#{item['number']} {item['name']}: {', '.join(item['missing'])}" for item in report["capabilities"] if not item["ok"]]
            raise RuntimeError("V5 frontier incomplete: " + "; ".join(missing))


__all__ = ["V5Capability", "V5_CAPABILITIES", "V5Frontier"]
