# Live autonomous trading

The civilization remains a 100-agent research system, but the market execution boundary is now explicit and configurable rather than pretending paper fills are live execution.

## Arbitrage

Set:

```text
LIVE_ARBITRAGE=1
LIVE_TRADING_CONFIRMATION=I_UNDERSTAND_LIVE_RISK
ARBITRAGE_BUY_EXCHANGE=<ccxt exchange id>
ARBITRAGE_SELL_EXCHANGE=<ccxt exchange id>
ARBITRAGE_BUY_API_KEY=<key>
ARBITRAGE_BUY_API_SECRET=<secret>
ARBITRAGE_SELL_API_KEY=<key>
ARBITRAGE_SELL_API_SECRET=<secret>
```

The scanner uses public live order books, validates fees/liquidity/net edge, and the live executor re-checks both venue prices immediately before submitting the two legs. The second-leg failure path is recorded as `partial` so an operator can reconcile the remaining exposure.

Limits are intentionally small by default:

- max arbitrage quote: `$25`
- minimum live edge: `0.75%`
- maximum quote age: `5s`
- explicit live-risk confirmation required

## Single-venue execution

The existing `LiveExecutionEngine` remains the guarded execution boundary for exchange market orders. It provides idempotency, slippage, position, daily-notional, daily-loss and kill-switch controls.

## Alpha and arbitrage email

`EmailAlertGateway` uses the existing SMTP environment and defaults to the configured civilization alert address. High-value arbitrage alerts include venue route and prices. Deployed alpha-token alerts include chain, contract address and explorer link when the launch provider returns a contract address.

Required SMTP variables are `CIVILIZATION_SMTP_HOST`, `CIVILIZATION_SMTP_USER`, and `CIVILIZATION_SMTP_PASSWORD`. Optional tuning variables are `CIVILIZATION_ALERT_MIN_CONFIDENCE`, `CIVILIZATION_ALERT_MIN_EDGE`, and `CIVILIZATION_ALERT_COOLDOWN`.

## Bankr

Bankr remains a separate token-launch adapter. A provider-side wallet balance rejection is not treated as a successful launch; no contract alert is emitted until a deployment response contains a deployed status and contract address.
