# Live Autonomous Trading Engine

This repository now has a real exchange execution path in addition to the research, backtesting, attribution, monitoring, and paper layers.

## Components

- `civilizations/autonomous_research.py` produces ranked opportunities from public market observations.
- `markets/live_controller.py` selects the highest-ranked eligible opportunity and derives a simple unlevered spot direction from exchange candles.
- `markets/live_execution.py` submits real CCXT orders, records lifecycle events, reconciles orders, and can cancel orders.
- `scripts/live_engine.py` runs the autonomous loop. It **does not fall back to paper trading**.

## Required environment

```text
LIVE_TRADING=1
LIVE_EXCHANGE=<ccxt exchange id>
LIVE_API_KEY=<exchange API key>
LIVE_API_SECRET=<exchange API secret>
```

Optional:

```text
LIVE_API_PASSWORD=<exchange password/passphrase when required>
LIVE_QUOTE_CURRENCY=USDT
LIVE_ORDER_QUOTE=10
LIVE_MIN_RISK_ADJUSTED=0.72
LIVE_MAX_ORDER_NOTIONAL=50
LIVE_MAX_TOTAL_NOTIONAL=200
LIVE_INTERVAL_SECONDS=30
LIVE_DATA_DIR=data/live
LIVE_TRADING_KILL_SWITCH=0
```

Credentials are read only from the process environment and are never written to the repository or order ledger.

## Start

```bash
python -m scripts.live_engine
```

The worker performs an exchange balance preflight before entering the loop. Every order is gated by the live arm, kill switch, positive amount, supported order type, per-order notional limit, and aggregate open exposure limit.

## Operational rule

Use an exchange API key restricted to trading permissions. Do not grant withdrawal permissions. Start with the configured notional limits and raise them deliberately only after observing the live order/reconciliation ledger.

The existing Bankr token-launch path remains separate; this live engine is for exchange spot trading and does not depend on Bankr.
