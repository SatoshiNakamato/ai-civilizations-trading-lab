from civilizations.ticker_brain import TickerBrain


def test_ticker_is_short_creative_and_clean():
    choice = TickerBrain().choose(
        thesis="liquidity and volume regime shift for SOL",
        agent="A001",
        cycle=7,
        existing={"SOL", "COIN", "TEST"},
    )
    assert 3 <= len(choice.symbol) <= 6
    assert choice.symbol.isalnum()
    assert choice.symbol == choice.symbol.upper()
    assert choice.symbol not in {"SOL", "COIN", "TEST"}


def test_ticker_is_reproducible():
    brain = TickerBrain()
    a = brain.choose(thesis="event driven repricing", agent="A002", cycle=4)
    b = brain.choose(thesis="event driven repricing", agent="A002", cycle=4)
    assert a == b
