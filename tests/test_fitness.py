import pytest

from civilizations.fitness import FitnessPolicy
from civilizations.scoring import score_forecast


def scores(probability, outcome, n=5):
    return [score_forecast(probability, outcome) for _ in range(n)]


def test_policy_requires_minimum_evidence():
    assert FitnessPolicy().evaluate(scores(.8, True, 4)) == float("-inf")


def test_policy_prefers_better_calibrated_predictions():
    policy = FitnessPolicy()
    good = policy.evaluate(scores(.8, True))
    bad = policy.evaluate(scores(.99, False))
    assert good > bad


def test_policy_version_and_weights_are_explicit():
    policy = FitnessPolicy(version="v2", brier_weight=.7, log_loss_weight=.3)
    assert policy.version == "v2"
    assert policy.brier_weight == pytest.approx(.7)


def test_policy_rejects_invalid_weights():
    with pytest.raises(ValueError):
        FitnessPolicy(brier_weight=-1)
    with pytest.raises(ValueError):
        FitnessPolicy(brier_weight=0, log_loss_weight=0)
