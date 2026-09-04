import json

import pytest

from execution.engine import ExecutionConfig, LiveExecutionEngine
from execution.ccxt_adapter import OrderResult
from execution.live_runtime import LiveTradingRuntime, TradeIntent


class FakeAdapter:
    def __init__(self):
        self.orders = []

    def ticker(self, symbol):
        return {"ask": 10.0, "bid": 10.0, "last": 10.0}

    def create_market_order(self, symbol, side, amount):
        result = OrderResult(f"order-{len(self.orders)+1}", symbol, side, amount, 10.0, "closed", {})
        self.orders.append(result)
        return result

    def fetch_order(self, order_id, symbol):
        return {"status": "closed", "filled": 1.0, "average": 10.0}


def engine(tmp_path, **kwargs):
    config = ExecutionConfig(require_live_confirmation=True, **kwargs)
    return LiveExecutionEngine(FakeAdapter(), tmp_path / "live.jsonl", config=config, clock=lambda: 1000.0)


def test_live_engine_requires_explicit_confirmation(monkeypatch, tmp_path):
    e = engine(tmp_path)
    with pytest.raises(RuntimeError, match="LIVE_TRADING_CONFIRMATION"):
        e.market_order("BTC/USDC", "buy", 1, 10, "signal-1")


def test_live_engine_submits_once_per_signal(monkeypatch, tmp_path):
    monkeypatch.setenv("LIVE_TRADING_CONFIRMATION", "I_UNDERSTAND_LIVE_RISK")
    e = engine(tmp_path)
    first = e.market_order("BTC/USDC", "buy", 1, 10, "signal-1")
    second = e.market_order("BTC/USDC", "buy", 1, 10, "signal-1")
    assert first["status"] == "submitted"
    assert second["status"] == "already_submitted"
    assert len(e.adapter.orders) == 1


def test_live_engine_enforces_order_and_daily_limits(monkeypatch, tmp_path):
    monkeypatch.setenv("LIVE_TRADING_CONFIRMATION", "I_UNDERSTAND_LIVE_RISK")
    e = engine(tmp_path, max_order_quote=10, max_daily_notional=15)
    with pytest.raises(RuntimeError, match="max quote size"):
        e.market_order("BTC/USDC", "buy", 2, 10, "large")
    e.market_order("BTC/USDC", "buy", 1, 10, "one")
    with pytest.raises(RuntimeError, match="daily live notional"):
        e.market_order("BTC/USDC", "buy", 1, 10, "two")


def test_live_engine_enforces_position_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("LIVE_TRADING_CONFIRMATION", "I_UNDERSTAND_LIVE_RISK")
    e = engine(tmp_path, max_position_quote=10)
    e.market_order("BTC/USDC", "buy", 1, 10, "one")
    with pytest.raises(RuntimeError, match="position quote limit"):
        e.market_order("BTC/USDC", "buy", 1, 10, "two")


def test_live_engine_enforces_slippage(monkeypatch, tmp_path):
    monkeypatch.setenv("LIVE_TRADING_CONFIRMATION", "I_UNDERSTAND_LIVE_RISK")
    e = engine(tmp_path, slippage_bps=10)
    e.adapter.ticker = lambda symbol: {"ask": 10.1, "bid": 10.1, "last": 10.1}
    with pytest.raises(RuntimeError, match="slippage guard"):
        e.market_order("BTC/USDC", "buy", 1, 10, "slippage")


def test_kill_switch_blocks_live_orders(monkeypatch, tmp_path):
    monkeypatch.setenv("LIVE_TRADING_CONFIRMATION", "I_UNDERSTAND_LIVE_RISK")
    e = engine(tmp_path)
    e.kill("test")
    with pytest.raises(RuntimeError, match="kill switch"):
        e.market_order("BTC/USDC", "buy", 1, 10, "blocked")


def test_runtime_rejects_low_confidence(monkeypatch, tmp_path):
    monkeypatch.setenv("LIVE_TRADING_CONFIRMATION", "I_UNDERSTAND_LIVE_RISK")
    e = engine(tmp_path)
    r = LiveTradingRuntime(e, min_confidence=.8)
    result = r.execute(TradeIntent("A001", "BTC/USDC", "buy", 1, 10, .5, "weak", "signal"))
    assert result["status"] == "rejected"
    assert not e.adapter.orders


def test_audit_contains_no_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("LIVE_TRADING_CONFIRMATION", "I_UNDERSTAND_LIVE_RISK")
    monkeypatch.setenv("TRADING_API_SECRET", "DO_NOT_LOG_THIS")
    e = engine(tmp_path)
    e.market_order("BTC/USDC", "buy", 1, 10, "signal")
    text = (tmp_path / "live.jsonl").read_text()
    assert "DO_NOT_LOG_THIS" not in text
    for line in text.splitlines():
        json.loads(line)
