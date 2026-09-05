import os

from civilizations.email_alerts import AlertCandidate, EmailAlertGateway
from execution.live_arbitrage import LiveArbitrageExecutor, LiveArbitrageConfig
from execution.ccxt_adapter import OrderResult
from civilizations.opportunities import Opportunity


class FakeLiveAdapter:
    def __init__(self, price):
        self.price = price
        self.orders = []

    def ticker(self, symbol):
        return {"ask": self.price, "bid": self.price, "last": self.price}

    def create_market_order(self, symbol, side, amount):
        order = OrderResult(f"{side}-{len(self.orders)+1}", symbol, side, amount, self.price, "closed", {})
        self.orders.append(order)
        return order


def opportunity():
    return Opportunity(
        opportunity_id="arb-1", category="arbitrage", asset="BTC",
        summary="buy low / sell high", confidence=.98, risk=.20,
        gross_edge=.02, fees=.005, slippage=.001, liquidity=1.0,
        sources=["live"], buy_venue="buy", sell_venue="sell",
        buy_price=100.0, sell_price=101.4, status="validated",
    )


def test_live_arbitrage_executes_both_legs(monkeypatch, tmp_path):
    monkeypatch.setenv("LIVE_ARBITRAGE", "1")
    monkeypatch.setenv("LIVE_TRADING_CONFIRMATION", "I_UNDERSTAND_LIVE_RISK")
    buy = FakeLiveAdapter(100.0)
    sell = FakeLiveAdapter(101.4)
    executor = LiveArbitrageExecutor(buy, sell, LiveArbitrageConfig(max_quote=25, min_net_edge=.005), tmp_path / "arb.jsonl", clock=lambda: 1000.0)
    result = executor.execute(opportunity(), quantity=.1)
    assert result.status == "executed"
    assert len(buy.orders) == 1
    assert len(sell.orders) == 1
    assert result.buy_order_id and result.sell_order_id


def test_live_arbitrage_requires_confirmation(monkeypatch, tmp_path):
    monkeypatch.setenv("LIVE_ARBITRAGE", "1")
    monkeypatch.delenv("LIVE_TRADING_CONFIRMATION", raising=False)
    executor = LiveArbitrageExecutor(FakeLiveAdapter(100), FakeLiveAdapter(101), LiveArbitrageConfig(), tmp_path / "arb.jsonl")
    try:
        executor.execute(opportunity(), quantity=.1)
    except RuntimeError as exc:
        assert "LIVE_TRADING_CONFIRMATION" in str(exc)
    else:
        raise AssertionError("live arbitrage must require explicit confirmation")


def test_email_alert_contains_token_metadata(monkeypatch):
    # Keep this unit test hermetic even when a developer/hosting environment
    # contains real AEON notification variables.
    monkeypatch.setenv("AEON_NOTIFICATION_ENABLED", "true")
    monkeypatch.setenv("AEON_NOTIFICATION_EMAIL_ENABLED", "true")
    monkeypatch.setenv("AEON_NOTIFICATION_MIN_SEVERITY", "HIGH")
    monkeypatch.setenv("AEON_NOTIFICATION_MAX_PER_CYCLE", "10")
    monkeypatch.setenv("AEON_NOTIFICATION_MAX_PER_DAY", "100")
    monkeypatch.setenv("AEON_NOTIFICATION_COOLDOWN_SECONDS", "0")
    monkeypatch.setenv("AEON_NOTIFICATION_DEDUP_ENABLED", "true")
    monkeypatch.setenv("AEON_NOTIFICATION_DEDUP_WINDOW_SECONDS", "3600")
    monkeypatch.setenv("CIVILIZATION_SMTP_HOST", "smtp.test")
    monkeypatch.setenv("CIVILIZATION_SMTP_USER", "user")
    monkeypatch.setenv("CIVILIZATION_SMTP_PASSWORD", "secret")
    monkeypatch.setenv("CIVILIZATION_ALERT_FROM", "alerts@example.com")
    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    gateway = EmailAlertGateway(recipient="alerts@example.com")
    candidate = AlertCandidate(
        title="Alpha launched", category="alpha-token", summary="launch", confidence=.95,
        edge=.02, risk=.2, token_address="0xABC", chain="base",
        url="https://basescan.org/token/0xABC", agent="A001",
    )
    assert gateway.send(candidate) is True
    assert "0xABC" in FakeSMTP.last_message
    assert "basescan.org/token/0xABC" in FakeSMTP.last_message


class FakeSMTP:
    last_message = ""

    def __init__(self, *args, **kwargs): pass
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def ehlo(self): pass
    def starttls(self): pass
    def login(self, user, password): pass
    def send_message(self, msg):
        FakeSMTP.last_message = msg.get_content()
