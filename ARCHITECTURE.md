# Architecture

The system is organized as a continuous autonomous decision loop:

```text
100-agent research mesh
  -> independent hypotheses
  -> cross-agent challenge / evidence exchange
  -> opportunity attribution
  -> ranking
  -> risk governor
  -> execution policy
  -> TradeIntent
  -> LIVE exchange adapter
  -> order reconciliation
  -> position / P&L observation
  -> strategy learning
  -> next cycle
```

## Execution modes

- **Paper** remains available for research validation.
- **Live** uses `execution.LiveExecutionEngine` and a CCXT exchange adapter. Live orders require `LIVE_TRADING=1` and explicit `LIVE_TRADING_CONFIRMATION=I_UNDERSTAND_LIVE_RISK`.
- Bankr token launching is a separate capability and is not required for spot trading.

## Live execution controls

The execution boundary enforces per-order notional limits, daily notional limits, a realized-loss kill switch, deterministic idempotency, append-only audit records, and exchange reconciliation. API credentials are read only from environment variables and are never persisted.

## Separation of responsibilities

- **Civilizations** coordinate research, debate, evidence, and strategy evolution.
- **Markets** provide opportunity, portfolio, observation, audit, and replay primitives.
- **Risk** decides whether a candidate is eligible for execution.
- **Execution** is the only component allowed to submit real orders.
- **Monitoring** reports health, exposure, order state, and lifecycle events.

Research never directly submits an order. It produces a `TradeIntent`; the live runtime validates the intent and passes it to the guarded execution engine.

## Persistence and recovery

Execution intents, submitted orders, and lifecycle events are persisted so a worker restart can reconcile exchange state instead of blindly submitting duplicates.
