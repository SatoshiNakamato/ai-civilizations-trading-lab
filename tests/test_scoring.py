import pytest

from civilizations.scoring import aggregate_scores, score_forecast


def test_brier_and_log_loss_reward_confident_correct_forecasts():
    score = score_forecast(0.9, True)
    assert score.brier == pytest.approx(0.01)
    assert score.log_loss == pytest.approx(-__import__("math").log(0.9))


def test_log_loss_penalizes_overconfidence_more_than_brier():
    confident = score_forecast(0.99, False)
    moderate = score_forecast(0.6, False)
    assert confident.log_loss > moderate.log_loss


def test_extreme_probabilities_are_floored_for_log_loss():
    score = score_forecast(1.0, False)
    assert score.log_loss == pytest.approx(-__import__("math").log(1e-6))


def test_aggregate_scores_is_empty_safe():
    assert aggregate_scores([]) == {"count": 0, "brier": 0.0, "log_loss": 0.0}
