from civilizations.endurance import EnduranceController
from civilizations.world_dynamics import WorldDynamics
from civilizations.civilization_platform import CivilizationPlatform


def test_startup_snapshot_samples_current_rss():
    controller = EnduranceController()
    snapshot = controller.snapshot(8)
    assert snapshot["rss_mb"] > 0
    assert snapshot["peak_rss_mb"] >= snapshot["rss_mb"]


def test_budget_stays_within_bounds():
    controller = EnduranceController(minimum_budget=2, maximum_budget=8)
    result = controller.check(tick=1, budget=8)
    assert 2 <= result["active_budget"] <= 8


def test_critical_pressure_reduces_budget():
    controller = EnduranceController(soft_limit_mb=0, hard_limit_mb=0, minimum_budget=2, maximum_budget=8)
    result = controller.check(tick=1, budget=8)
    assert result["level"] == "critical"
    assert result["active_budget"] == 2
    assert result["pressure_events"] == 1


def test_twenty_world_systems_are_registered_and_bounded(tmp_path):
    platform = CivilizationPlatform(root=str(tmp_path / "aeon-test-world"), seed=7, active_budget=2)
    for aid in ("A001", "A002"):
        platform.register(aid)
    systems = WorldDynamics(platform, seed=7, history_limit=32)
    systems.tick(["A001", "A002"], 5)
    snapshot = systems.snapshot()
    assert snapshot["feature_count"] == 20
    assert len(snapshot["history"]) <= 16
    assert len(platform.knowledge) <= 300
    assert len(platform.science) <= 200
    assert len(platform.artifacts) <= 300


def test_dynamics_updates_contracts_markets_and_migration(tmp_path):
    platform = CivilizationPlatform(root=str(tmp_path / "aeon-test-world-2"), seed=11, active_budget=2)
    platform.register("A001")
    platform.register("A002")
    systems = WorldDynamics(platform, seed=11)
    for tick in range(1, 11):
        systems.tick(["A001", "A002"], tick)
    assert platform.contracts
    assert "AEON" in platform.markets["credits"]["prices"]
    assert platform.metrics["social_interactions"] > 0
    assert systems.lineage
