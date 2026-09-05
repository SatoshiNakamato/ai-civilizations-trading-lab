from civilizations.arena import CivilizationArena
from civilizations.tournament import CivilizationTournament


def _resolved(arena, cid, offset):
    c = arena.commit(cid, f"agent-{offset}", "BTCUSDT", "4h", .8, created_at=100 + offset)
    arena.submit(c)
    arena.resolve(__import__("civilizations.arena", fromlist=["ForecastOutcome"]).ForecastOutcome(c.forecast_id, True, 200 + offset, "external://fixture"))


def test_tournament_records_rankings_and_selection():
    arena = CivilizationArena()
    for i in range(20):
        _resolved(arena, "CIV-A", i)
        _resolved(arena, "CIV-B", i + 100)
    tournament = CivilizationTournament(arena)
    record = tournament.run(["CIV-A", "CIV-B"], survivors=1, generation=3, tournament_id="T-3")
    assert record.tournament_id == "T-3"
    assert record.selected == ("CIV-A", "CIV-B")[:1]
    assert len(record.rankings) == 2
    assert len(record.record_hash) == 64


def test_tournament_deduplicates_participants():
    arena = CivilizationArena()
    tournament = CivilizationTournament(arena)
    record = tournament.run(["CIV-A", "CIV-A"], survivors=1, generation=0, tournament_id="T-0")
    assert record.participants == ("CIV-A",)
