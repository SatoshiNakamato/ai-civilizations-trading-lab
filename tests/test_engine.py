import pytest

from civilizations.arena import ArenaConfig, CivilizationArena
from civilizations.engine import CivilizationCycle


def populated_arena():
    arena = CivilizationArena(ArenaConfig(min_resolved=2))
    for cid, events in (("CIV-A", (True, True, True, True, True)), ("CIV-B", (False, True, False, True, False))):
        for i, event in enumerate(events):
            arena.record_prediction(cid, f"PAIR{i}USDT", .8 if event else .2, event, agent_id=f"agent-{i}", horizon="1h", created_at=10 + i, observed_at=11 + i)
    return arena


def test_cycle_runs_tournament_then_generation():
    cycle = CivilizationCycle(populated_arena())
    result = cycle.run(("CIV-A", "CIV-B"), survivors=1, generation=1, created_at=20, tournament_id="t1")
    assert result.tournament.selected == ("CIV-A",)
    assert result.generation.parents == ("CIV-A",)
    assert result.generation.children == ("CIV-A.g2.1",)
    assert cycle.audit.verify()
    assert cycle.identity(result)


def test_cycle_never_invents_evidence():
    arena = CivilizationArena(ArenaConfig(min_resolved=2))
    cycle = CivilizationCycle(arena)
    with pytest.raises(ValueError, match="survived|selected"):
        cycle.run(("CIV-A",), survivors=1, generation=1, created_at=20)
    assert not arena.commitments
    assert not arena.outcomes


def test_cycle_rejects_impossible_survivor_count():
    with pytest.raises(ValueError, match="exceed"):
        CivilizationCycle(populated_arena()).run(("CIV-A",), survivors=2, generation=1)
