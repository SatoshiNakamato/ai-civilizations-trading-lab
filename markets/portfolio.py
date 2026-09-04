from __future__ import annotations

from dataclasses import asdict, dataclass
import time
import uuid


class Portfolio:
    def __init__(self): self.positions={}; self.realized_pnl=0.0
    def open(self,key,notional): self.positions[key]=self.positions.get(key,0.0)+notional
    def close(self,key,pnl): self.positions.pop(key,None); self.realized_pnl+=pnl
    @property
    def exposure(self): return sum(abs(x) for x in self.positions.values())
    def snapshot(self): return {'positions':dict(self.positions),'exposure':self.exposure,'realized_pnl':self.realized_pnl}


@dataclass
class PaperOrder:
    order_id: str
    agent: str
    symbol: str
    side: str
    notional: float
    status: str
    created_at: float
    filled_at: float = 0.0
    entry_price: float = 0.0
    mark_price: float = 0.0
    realized_pnl: float = 0.0

    def snapshot(self): return asdict(self)


class PaperExecutionEngine:
    """Deterministic, cash-aware paper execution and observation layer."""
    def __init__(self, initial_cash=1000.0, max_position_notional=100.0):
        if initial_cash < 0 or max_position_notional <= 0: raise ValueError('invalid paper execution limits')
        self.initial_cash=float(initial_cash); self.cash=float(initial_cash)
        self.max_position_notional=float(max_position_notional)
        self.orders={}; self.positions={}; self.started_at=time.time()

    def open(self, agent, symbol, notional, price):
        notional=float(notional); price=float(price)
        if not agent or not symbol: raise ValueError('agent and symbol are required')
        if notional <= 0 or price <= 0: raise ValueError('notional and price must be positive')
        if notional > self.max_position_notional: raise ValueError('paper position limit exceeded')
        if notional > self.cash: raise RuntimeError('insufficient paper cash')
        key=f'{agent}:{symbol}'
        if key in self.positions: raise RuntimeError('paper position already open')
        now=time.time(); order=PaperOrder(uuid.uuid4().hex,agent,symbol,'buy',notional,'filled',now,now,price,price)
        self.orders[order.order_id]=order; self.positions[key]=order; self.cash-=notional
        return order

    def mark(self, agent, symbol, price):
        price=float(price)
        if price <= 0: raise ValueError('price must be positive')
        order=self.positions.get(f'{agent}:{symbol}')
        if order is None: raise KeyError(f'{agent}:{symbol}')
        order.mark_price=price; return order

    def close(self, agent, symbol, price):
        order=self.mark(agent,symbol,price)
        exit_value=order.notional*(order.mark_price/order.entry_price)
        order.realized_pnl=exit_value-order.notional; order.status='closed'
        self.cash+=exit_value; self.positions.pop(f'{agent}:{symbol}',None); return order

    def snapshot(self):
        market_value=sum(o.notional*(o.mark_price/o.entry_price) for o in self.positions.values())
        unrealized=market_value-sum(o.notional for o in self.positions.values())
        realized=sum(o.realized_pnl for o in self.orders.values() if o.status=='closed')
        return {'cash':self.cash,'initial_cash':self.initial_cash,'equity':self.cash+market_value,
                'realized_pnl':realized,'unrealized_pnl':unrealized,
                'open_positions':[o.snapshot() for o in self.positions.values()],
                'orders':[o.snapshot() for o in self.orders.values()],
                'uptime_seconds':time.time()-self.started_at}
