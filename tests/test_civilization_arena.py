from pytest import approx

from civilizations.arena import CivilizationArena, ForecastOutcome


def test_commitment_is_immutable_and_resolves_once():
    arena = CivilizationArena()
    commitment = arena.commit("CIV-A", "A001", "BTCUSDT", "4h", 0.8, forecast_id="f1", created_at=100)
    arena.submit(commitment)
    arena.resolve(ForecastOutcome("f1", True, 200, "external-test-source"))
    assert arena.outcomes["f1"].event is True
    assert arena.resolve(ForecastOutcome("f1", True, 200, "external-test-source")) == arena.outcomes["f1"]


def test_resolution_rejects_outcome_before_commitment():
    arena = CivilizationArena()
    arena.submit(arena.commit("CIV-A", "A001", "BTCUSDT", "4h", 0.8, forecast_id="f1", created_at=100))
    try:
        arena.resolve(ForecastOutcome("f1", True, 99, "external"))
        assert False, "expected timestamp validation"
    except ValueError as exc:
        assert "precede" in str(exc)


def test_brier_and_calibration_are_objective():
    arena = CivilizationArena()
    arena.config.min_resolved = 2
    for i, probability in enumerate((0.9, 0.1), 1):
        c = arena.commit("CIV-A", f"A{i:03d}", "BTCUSDT", "4h", probability, forecast_id=f"f{i}", created_at=100 + i)
        arena.submit(c)
        arena.resolve(ForecastOutcome(f"f{i}", i == 1, 200 + i, "external"))
    score = arena.score("CIV-A")
    assert score.resolved == 2
    assert score.brier_score == approx(0.01)
    assert score.calibration_error == approx(0.1)
    assert score.sample_sufficient is True
    assert 0.0 <= score.fitness <= 1.0


def test_leaderboard_requires_enough_resolved_samples_for_selection():
    arena = CivilizationArena()
    arena.config.min_resolved = 2
    for cid, p in (("CIV-A", 0.9), ("CIV-B", 0.6)):
        c = arena.commit(cid, "A001", "BTCUSDT", "4h", p, forecast_id=cid, created_at=100)
        arena.submit(c)
        arena.resolve(ForecastOutcome(cid, True, 200, "external"))
    board = arena.leaderboard()
    assert board[0].sample_sufficient is False
    assert {s.civilization_id for s in board} == {"CIV-A", "CIV-B"}


def test_missing_external_source_is_rejected():
    arena = CivilizationArena()
    arena.submit(arena.commit("CIV-A", "A001", "BTCUSDT", "4h", 0.5, forecast_id="f1", created_at=100))
    try:
        arena.resolve(ForecastOutcome("f1", True, 200, ""))
        assert False, "expected source validation"
    except ValueError as exc:
        assert "source" in str(exc)
