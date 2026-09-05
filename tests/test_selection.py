import math

from civilizations.fitness import FitnessPolicy
from civilizations.scoring import score_forecast
from civilizations.selection import rank_civilizations


def test_ranking_uses_explicit_policy_and_deterministic_ties():
    scores = {
        "CIV-B": [score_forecast(.8, True)] * 5,
        "CIV-A": [score_forecast(.8, True)] * 5,
        "CIV-C": [score_forecast(.99, False)] * 5,
    }
    ranked = rank_civilizations(scores, policy=FitnessPolicy(version="v1"))
    assert [x.civilization_id for x in ranked] == ["CIV-A", "CIV-B", "CIV-C"]
    assert ranked[0].fitness > ranked[-1].fitness


def test_under_evidenced_civilization_cannot_win_with_one_lucky_forecast():
    scores = {
        "CIV-A": [score_forecast(.8, True)] * 5,
        "CIV-B": [score_forecast(.99, True)],
    }
    ranked = rank_civilizations(scores)
    assert ranked[0].civilization_id == "CIV-A"
    assert math.isinf(ranked[1].fitness) and ranked[1].fitness < 0
