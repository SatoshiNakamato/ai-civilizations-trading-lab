"""Release-readiness invariants for AEON's core runtime."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReleaseChecklist:
    tests_required: bool = True
    external_outcomes_required: bool = True
    synthetic_market_data_forbidden: bool = True
    audit_required: bool = True
    lineage_required: bool = True

    def as_dict(self) -> dict[str, bool]:
        return {
            "tests_required": self.tests_required,
            "external_outcomes_required": self.external_outcomes_required,
            "synthetic_market_data_forbidden": self.synthetic_market_data_forbidden,
            "audit_required": self.audit_required,
            "lineage_required": self.lineage_required,
        }

    def ready(self, *, tests_passed: bool, external_provider_configured: bool, audit_verified: bool, lineage_enabled: bool) -> bool:
        return all((tests_passed, external_provider_configured, audit_verified, lineage_enabled))
