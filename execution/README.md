# Live Trading Engine

This package is the real-money execution boundary. It is not a simulator.

## Required environment

```text
LIVE_TRADING=1
TRADING_EXCHANGE=coinbase
TRADING_API_KEY=<exchange key>
TRADING_API_SECRET=<exchange secret>
LIVE_TRADING_CONFIRMATION=I_UNDERSTAND_LIVE_RISK
```

Optional controls:

```text
LIVE_MAX_ORDER_QUOTE=25
LIVE_MAX_POSITION_QUOTE=100
LIVE_MAX_DAILY_LOSS=25
LIVE_MAX_DAILY_NOTIONAL=250
LIVE_MAX_SLIPPAGE_BPS=100
```

Credentials are read at runtime and are never written to the audit ledger.

## Safety properties

1. Explicit live-mode and confirmation gates.
2. Per-order and daily notional limits.
3. Daily realized-loss kill switch.
4. Deterministic idempotency keys prevent duplicate submissions after restarts.
5. Append-only execution audit.
6. Exchange reconciliation on every worker interval.
7. Live execution remains behind a decision boundary: research produces a `TradeIntent`; only the live runtime may submit it.

The engine does not claim profitability. A strategy must earn its execution eligibility through the existing research, evidence, ranking, and risk pipeline.
