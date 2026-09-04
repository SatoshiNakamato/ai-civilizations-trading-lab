import json

import pytest

from markets.live_execution import LiveExecutionEngine, LiveExecutionError


class FakeExchange:
    id = "fake"

    def __init__(self):
        self.orders = []

    def fetch_ticker(self, symbol):
        return {"last": 100.0, "ask": 100.0, "bid": 99.0}

    def fetch_balance(self):
        return {"free": {"USDT": 1000}}

    def create_order(self, symbol, order_type, side, amount, price, params):
        order = {"id": f"o-{len(self.orders)+1}", "symbol": symbol, "status": "open", "cost": amount * 100}
        self.orders.append(order)
        return order

    def fetch_order(self, order_id, symbol):
        return {"id": order_id, "symbol": symbol, "status": "closed"}

    def cancel_order(self, order_id, symbol):
        return {"id": order_id, "symbol": symbol, "status": "canceled"}


def make_engine(tmp_path, monkeypatch, exchange=None):
    monkeypatch.setenv("LIVE_TRADING", "1")
    monkeypatch.setenv("LIVE_TRADING_KILL_SWITCH", "0")
    monkeypatch.setenv("LIVE_MAX_ORDER_NOTIONAL", "50")
    return LiveExecutionEngine(str(tmp_path / "live.jsonl"), exchange or FakeExchange())


def test_live_execution_requires_arm(monkeypatch, tmp_path):
    monkeypatch.delenv("LIVE_TRADING", raising=False)
    with pytest.raises(LiveExecutionError, match="LIVE_TRADING=1"):
        LiveExecutionEngine.from_env(str(tmp_path / "live.jsonl"))


def test_live_execution_kill_switch(monkeypatch, tmp_path):
    monkeypatch.setenv("LIVE_TRADING", "1")
    monkeypatch.setenv("LIVE_TRADING_KILL_SWITCH", "1")
    with pytest.raises(LiveExecutionError, match="kill switch"):
        LiveExecutionEngine.from_env(str(tmp_path / "live.jsonl"))


def test_live_order_is_idempotent(tmp_path, monkeypatch):
    engine = make_engine(tmp_path, monkeypatch)
    intent = engine.new_intent("A001", "BTC/USDT", "buy", 0.1)
    first = engine.submit(intent)
    second = engine.submit(intent)
    assert first == second
    assert len(engine.exchange.orders) == 1


def test_live_order_notional_guard(tmp_path, monkeypatch):
    engine = make_engine(tmp_path, monkeypatch)
    intent = engine.new_intent("A001", "BTC/USDT", "buy", 1.0)
    with pytest.raises(LiveExecutionError, match="exceeds max"):
        engine.submit(intent)


def test_reconcile_and_cancel(tmp_path, monkeypatch):
    engine = make_engine(tmp_path, monkeypatch)
    assert engine.reconcile("o-1", "BTC/USDT")["order"]["status"] == "closed"
    assert engine.cancel("o-1", "BTC/USDT")["order"]["status"] == "canceled"
    records = [json.loads(x) for x in (tmp_path / "live.jsonl").read_text().splitlines()]
    assert {r["status"] for r in records} >= {"reconciled", "cancelled"}
