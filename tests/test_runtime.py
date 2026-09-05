import pytest

from civilizations.arena import ArenaConfig, CivilizationArena
from civilizations.engine import CivilizationCycle
from civilizations.runtime import CivilizationRuntime, RuntimeConfig


def arena():
    a = CivilizationArena(ArenaConfig(min_resolved=2))
    for cid, events in (("CIV-A", (True, True)), ("CIV-B", (False, True))):
        for i, event in enumerate(events):
            a.record_prediction(cid, f"PAIR{i}USDT", .8 if event else .2, event, agent_id=f"agent-{i}", horizon="1h", created_at=10+i, observed_at=11+i)
    return a


def test_runtime_step_returns_audited_cycle():
    runtime = CivilizationRuntime(CivilizationCycle(arena()))
    result = runtime.step(("CIV-A", "CIV-B"), config=RuntimeConfig(survivors=1, generation=1), markets=("PAIR0USDT", "PAIR1USDT"))
    assert result.audit_valid
    assert result.cycle.tournament.selected == ("CIV-A",)
    assert result.cycle.generation.children == ("CIV-A.g2.1",)
    assert len(result.run_id) == 24


def test_runtime_never_creates_missing_evidence():
    runtime = CivilizationRuntime(CivilizationCycle(CivilizationArena(ArenaConfig(min_resolved=2))))
    with pytest.raises(ValueError, match="evidence-qualified"):
        runtime.step(("CIV-A",), config=RuntimeConfig(survivors=1, generation=1))
