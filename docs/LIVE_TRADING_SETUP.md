# Live Trading Setup

The engine can submit real exchange orders through CCXT. It does not automatically acquire funds or bypass exchange restrictions.

## 1. Install

```bash
pip install -r requirements.txt
```

## 2. Configure secrets on the host

Set these environment variables in the host secret manager (never in Git):

```text
LIVE_TRADING=1
TRADING_EXCHANGE=coinbase
TRADING_API_KEY=...
TRADING_API_SECRET=...
LIVE_TRADING_CONFIRMATION=I_UNDERSTAND_LIVE_RISK
```

Optional limits:

```text
LIVE_MAX_ORDER_QUOTE=25
LIVE_MAX_POSITION_QUOTE=100
LIVE_MAX_DAILY_LOSS=25
LIVE_MAX_DAILY_NOTIONAL=250
LIVE_MAX_SLIPPAGE_BPS=100
LIVE_INTERVAL=30
```

## 3. Preflight

```bash
python -m scripts.live_preflight
```

The preflight checks configuration only. It does not place an order.

## 4. Run the live reconciliation worker

```bash
python -m simulation.live_worker
```

The worker reconciles submitted orders continuously. The civilization runtime should create `TradeIntent` objects only after research, evidence, ranking, and risk approval.

## 5. Production rule

Start with conservative limits and verify exchange permissions, symbol precision, minimum order sizes, fees, and account funding. The engine intentionally refuses to submit without the explicit confirmation string.

The software cannot guarantee profits. Live execution is a real financial operation and exchange/API failures, latency, slippage, liquidity, and strategy error can cause losses.
