from civilizations.autonomous_research import AutonomousResearchEngine
from markets.end_to_end import TradingCivilizationV1


def test_research_engine_generates_and_challenges_hypotheses(tmp_path):
    engine = AutonomousResearchEngine()
    opportunities = engine.cycle(["A001", "A002", "A003", "A004"], 1)
    assert opportunities
    assert all(x.debate.supporters > 0 for x in opportunities)
    assert all(x.debate.challengers > 0 for x in opportunities)
    assert all(0 <= x.risk_adjusted <= 1 for x in opportunities)


def test_hosted_cycle_has_real_stages_and_bankr_plan(tmp_path):
    civ = TradingCivilizationV1(runtime=None, agents=["A001", "A002", "A003", "A004"], data_dir=str(tmp_path))
    result = civ.cycle()
    stages = {x["stage"]: x for x in result["telemetry"]["stages"]}
    assert stages["hypotheses"]["count"] > 0
    assert stages["debate"]["count"] > 0
    assert stages["evidence"]["count"] > 0
    assert "bankr_plans" in result
    assert result["bankr_plans"] == []
    assert stages["bankr"]["status"] == "disabled"
