from civilizations.frontier import FrontierCivilizationEngine


def test_frontier_engine_is_bounded_and_deterministic():
    a = FrontierCivilizationEngine(seed=7, civilization_count=4)
    b = FrontierCivilizationEngine(seed=7, civilization_count=4)
    sa = a.tick_once()
    sb = b.tick_once()
    assert sa["civilizations"] == 4
    assert sa["tick"] == 1
    assert sa["championship"] == sb["championship"]
    assert sa["safety"]["real_trading"] is False
    assert sa["safety"]["self_replication"] is False


def test_frontier_stress_test_preserves_nonnegative_capital():
    engine = FrontierCivilizationEngine(seed=11, civilization_count=3)
    engine.economic_stress_test(1.0)
    assert all(c.capital >= 0 for c in engine.civilizations.values())
    ranking = engine.championship_round()
    assert [x["rank"] for x in ranking] == [1, 2, 3]


def test_signal_challenge_and_propagation_are_local():
    engine = FrontierCivilizationEngine(seed=3, civilization_count=3)
    signal = engine.emit_signal("CIV-001", "test hypothesis", 0.9, 0.9)
    assert engine.challenge(signal) in (True, False)
    assert engine.propagate(signal, "CIV-002") in (True, False)
    assert all(e["target"] in {"CIV-002", "ALL"} for e in engine.events)
