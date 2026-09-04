from civilizations.live_arbitrage import LiveArbitrageScanner, Quote


def test_live_spread_creates_candidate():
    quotes = [
        Quote("cheap", "BTC-USD", bid=99_900, ask=100_000),
        Quote("rich", "BTC-USD", bid=102_000, ask=102_100),
    ]
    o = LiveArbitrageScanner.from_quotes(quotes)
    assert o is not None
    assert o.buy_venue == "cheap"
    assert o.sell_venue == "rich"
    assert abs(o.gross_edge - 0.02) < 1e-9


def test_no_cross_venue_spread_returns_none():
    quotes = [Quote("one", "BTC-USD", 100_000, 100_100)]
    assert LiveArbitrageScanner.from_quotes(quotes) is None


def test_scanner_uses_feed_and_engine(tmp_path):
    class Feed:
        def snapshot(self):
            return [
                Quote("cheap", "BTC-USD", 99_900, 100_000),
                Quote("rich", "BTC-USD", 102_000, 102_100),
            ]

    from civilizations.opportunities import OpportunityEngine
    scanner = LiveArbitrageScanner(Feed(), OpportunityEngine(str(tmp_path / "audit.jsonl")))
    result = scanner.scan_once()
    assert result is not None
    assert result.status == "validated"
    assert result.net_edge > 0
