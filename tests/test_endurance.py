from civilizations.endurance import EnduranceController


def test_startup_snapshot_samples_rss():
    controller = EnduranceController()
    snapshot = controller.snapshot(8)
    assert snapshot["rss_mb"] > 0
    assert snapshot["peak_rss_mb"] >= snapshot["rss_mb"]


def test_budget_stays_within_bounds():
    controller = EnduranceController(minimum_budget=2, maximum_budget=8)
    result = controller.check(tick=1, budget=8)
    assert 2 <= result["active_budget"] <= 8


def test_critical_pressure_reduces_budget():
    controller = EnduranceController(
        soft_limit_mb=0,
        hard_limit_mb=0,
        minimum_budget=2,
        maximum_budget=8,
    )
    result = controller.check(tick=1, budget=8)
    assert result["level"] == "critical"
    assert result["active_budget"] == 2
    assert result["pressure_events"] == 1
