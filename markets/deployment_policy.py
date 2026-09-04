from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class DeploymentDecision:
    allowed: bool
    reason: str

class DeploymentPolicy:
    """Final deterministic gate before a live token deployment."""
    def __init__(self, min_score=0.62, max_risk=0.35, max_daily_per_agent=3):
        self.min_score=float(min_score); self.max_risk=float(max_risk); self.max_daily_per_agent=int(max_daily_per_agent)
    def evaluate(self, plan, *, deployments_today=0, authenticated=False):
        if not authenticated: return DeploymentDecision(False, "agent Bankr credential is not authenticated")
        if plan.score < self.min_score: return DeploymentDecision(False, "research score below deployment threshold")
        if getattr(plan, "risk", 0.0) > self.max_risk: return DeploymentDecision(False, "risk exceeds deployment threshold")
        if deployments_today >= self.max_daily_per_agent: return DeploymentDecision(False, "agent deployment quota reached")
        return DeploymentDecision(True, "approved")
