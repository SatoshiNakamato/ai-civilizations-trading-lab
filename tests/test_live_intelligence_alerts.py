from civilizations.live_alpha import AlphaToken, LiveAlphaScanner
from civilizations.email_alerts import EmailAlertGateway
from civilizations.live_arbitrage import LiveArbitrageScanner, Quote


def test_alpha_alert_contains_contract_and_dex_link(monkeypatch):
    sent = []
    monkeypatch.setattr(EmailAlertGateway, "send", lambda self, candidate: sent.append(candidate) or True)
    scanner = LiveAlphaScanner(gateway=EmailAlertGateway())
    token = AlphaToken("base", "0xABC", "CAT", "Cat", "0xPAIR", "https://dexscreener.com/base/0xPAIR", 0.001, 25000, 50000, 8, 35, 120, 70, 50, 6, 0.91)
    assert scanner.alert(token)
    assert sent[0].category == "alpha-token"
    assert sent[0].token_address == "0xABC"
    assert sent[0].url.endswith("/base/0xPAIR")


def test_arbitrage_candidate_preserves_manual_route():
    candidate = LiveArbitrageScanner.from_quotes([
        Quote("coinbase", "BTC-USD", 100.0, 100.5),
        Quote("kraken", "BTC-USD", 102.0, 102.5),
    ])
    assert candidate is not None
    assert candidate.buy_venue == "coinbase"
    assert candidate.sell_venue == "kraken"
    assert candidate.buy_price == 100.5
    assert candidate.sell_price == 102.0
