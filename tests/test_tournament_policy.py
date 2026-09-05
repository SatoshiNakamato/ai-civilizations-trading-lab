from civilizations.arena import CivilizationArena
from civilizations.fitness import FitnessPolicy
from civilizations.tournament import CivilizationTournament


def _populate(arena, cid, probability, outcome, count):
    for i in range(count):
        c = arena.commit(cid, f"agent-{i}", f"PAIR{i}USDT", "1h", probability, created_at=100 + i)
        arena.submit(c)
        arena.resolve(__import__("civilizations.arena", fromlist=["ForecastOutcome"]).ForecastOutcome(c.forecast_id, outcome, 200 + i, "feed"))


def test_tournament_uses_injected_policy_for_selection():
    arena = CivilizationArena()
    _populate(arena, "CIV-GOOD", .8, True, 5)
    _populate(arena, "CIV-BAD", .99, False, 5)
    tournament = CivilizationTournament(arena, policy=FitnessPolicy(version="test-v1", minimum_forecasts=5))
    record = tournament.run(["CIV-BAD", "CIV-GOOD"], survivors=1, generation=1, tournament_id="t1")
    assert record.selected == ("CIV-GOOD",)
    assert tournament.snapshot()["policy_version"] == "test-v1"


def test_tournament_excludes_under_evidenced_civilization():
    arena = CivilizationArena()
    _populate(arena, "CIV-A", .8, True, 5)
    _populate(arena, "CIV-LUCKY", .99, True, 1)
    tournament = CivilizationTournament(arena)
    record = tournament.run(["CIV-LUCKY", "CIV-A"], survivors=1, generation=2, tournament_id="t2")
    assert record.selected == ("CIV-A",)
    assert "CIV-LUCKY" in record.excluded
