from civilizations.opportunities import OpportunityEngine
from markets.multi_exchange_arbitrage import MarketQuote, MultiExchangeArbitrageScanner


class FakeExchange:
    def __init__(self, book):
        self.book = book
        self.has = {"fetchTickers": False}

    def fetch_order_book(self, symbol, limit):
        return self.book


def test_depth_verification_rejects_insufficient_liquidity(tmp_path):
    scanner = MultiExchangeArbitrageScanner(
        engine=OpportunityEngine(str(tmp_path / "audit.jsonl")),
        exchanges=("cheap", "rich"),
        notional_usd=100,
    )
    scanner._clients["cheap"] = FakeExchange({"timestamp": 1_000_000, "asks": [[100, 0.1]], "bids": []})
    scanner._clients["rich"] = FakeExchange({"timestamp": 1_000_000, "asks": [], "bids": [[105, 0.1]]})
    scanner.max_quote_age_seconds = 10_000_000
    buy = MarketQuote("cheap", "BTC/USDT", 99, 100, 1, 1, 1_000_000)
    sell = MarketQuote("rich", "BTC/USDT", 104, 105, 1, 1, 1_000_000)
    assert scanner._depth_verify(buy, sell) is None


def test_opportunity_is_marked_executable_only_after_depth_check(tmp_path):
    scanner = MultiExchangeArbitrageScanner(
        engine=OpportunityEngine(str(tmp_path / "audit.jsonl")),
        exchanges=("cheap", "rich"),
        notional_usd=100,
    )
    scanner._clients["cheap"] = FakeExchange({"timestamp": 1_000_000, "asks": [[100, 2]], "bids": []})
    scanner._clients["rich"] = FakeExchange({"timestamp": 1_000_000, "asks": [], "bids": [[105, 2]]})
    scanner.max_quote_age_seconds = 10_000_000
    scanner._quotes = {
        "BTC/USDT": [
            MarketQuote("cheap", "BTC/USDT", 99, 100, 2, 2, 1_000_000),
            MarketQuote("rich", "BTC/USDT", 105, 106, 2, 2, 1_000_000),
        ]
    }
    opportunities = scanner._opportunities()
    assert opportunities
    opportunity = opportunities[0]
    assert opportunity.executable is True
    assert opportunity.observed_at > 0
    assert opportunity.quantity > 0
    assert opportunity.notional_usd > 0
    assert opportunity.buy_depth >= opportunity.quantity
    assert opportunity.sell_depth >= opportunity.quantity
    assert opportunity.net_edge > 0


def test_stale_order_book_never_becomes_alertable(tmp_path):
    scanner = MultiExchangeArbitrageScanner(
        engine=OpportunityEngine(str(tmp_path / "audit.jsonl")),
        exchanges=("cheap", "rich"),
    )
    scanner._clients["cheap"] = FakeExchange({"timestamp": 1, "asks": [[100, 2]], "bids": []})
    scanner._clients["rich"] = FakeExchange({"timestamp": 1, "asks": [], "bids": [[105, 2]]})
    scanner.max_quote_age_seconds = 1
    buy = MarketQuote("cheap", "BTC/USDT", 99, 100, 2, 2, 1)
    sell = MarketQuote("rich", "BTC/USDT", 105, 106, 2, 2, 1)
    assert scanner._depth_verify(buy, sell) is None
