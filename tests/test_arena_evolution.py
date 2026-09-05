from civilizations.arena import ArenaConfig, CivilizationArena
from civilizations.arena_evolution import ArenaEvolution


def _populate(arena, cid, offset):
    for i in range(2):
        c = arena.commit(cid, f"A{i}", "BTCUSDT", "4h", .9, forecast_id=f"{cid}-{i}", created_at=10 + offset + i)
        arena.submit(c)
        from civilizations.arena import ForecastOutcome
        arena.resolve(ForecastOutcome(c.forecast_id, True, 20 + offset + i, "external://fixture"))


def test_advance_only_reproduces_sample_sufficient_survivors():
    arena = CivilizationArena(ArenaConfig(min_resolved=2))
    _populate(arena, "CIV-A", 0)
    _populate(arena, "CIV-B", 100)
    evolution = ArenaEvolution(arena)
    evolution.register("CIV-A")
    evolution.register("CIV-B")
    record = evolution.advance(("CIV-A", "CIV-B"), survivors=1, offspring_factory=lambda parent, generation: f"{parent}-g{generation}")
    assert record.survivors == ("CIV-A", "CIV-B")[:1]
    assert len(record.offspring) == 1
    assert evolution.lineages[record.offspring[0]].parent_ids == record.survivors
    assert evolution.generation == 1


def test_generation_history_is_auditable():
    arena = CivilizationArena(ArenaConfig(min_resolved=1))
    _populate(arena, "CIV-A", 0)
    evolution = ArenaEvolution(arena)
    evolution.register("CIV-A")
    record = evolution.advance(("CIV-A",), survivors=1, offspring_factory=lambda parent, generation: f"child-{generation}")
    snapshot = evolution.snapshot()
    assert snapshot["generations_completed"] == 1
    assert snapshot["lineage"][1]["parent_ids"] == ["CIV-A"]
    assert record.selection.generation == 0
