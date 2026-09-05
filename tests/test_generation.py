import pytest

from civilizations.arena import CivilizationArena
from civilizations.generation import GenerationEngine
from civilizations.tournament import CivilizationTournament


def test_generation_advance_binds_selected_parents_to_children():
    arena = CivilizationArena()
    for cid in ("CIV-A", "CIV-B"):
        for _ in range(5):
            arena.record_prediction(cid, "BTCUSDT", .8, True)
    tournament = CivilizationTournament(arena)
    result = tournament.run(("CIV-A", "CIV-B"), survivors=1, generation=1, tournament_id="t1")
    engine = GenerationEngine(tournament)
    generation = engine.advance(result, created_at=20)
    assert generation.generation == 2
    assert generation.parents == result.selected
    assert len(generation.children) == 1
    assert engine.lineage.ancestors(generation.children[0]) == result.selected


def test_generation_rejects_foreign_tournament_record():
    arena = CivilizationArena()
    tournament = CivilizationTournament(arena)
    other = CivilizationTournament(arena)
    with pytest.raises(ValueError, match="not owned"):
        GenerationEngine(tournament).advance(other.run(("CIV-A",), survivors=1, generation=1, tournament_id="foreign"))
