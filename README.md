# AI Civilizations Trading Lab

A research-first multi-agent market intelligence system: 100 simulated AI civilizations with distinct personas, expertise, risk preferences, communication, strategy evolution, arbitrage research, prediction-market analysis, and cooperative portfolio intelligence.

## Vision

The civilization behaves like a society of specialized researchers. Agents observe markets, form hypotheses, debate, share strategy memes, mutate and recombine ideas, run experiments, and learn from measured outcomes. The shared objective is to improve risk-adjusted performance while preserving capital.

The runtime supports a governed Bankr token-launch proof-of-life mode: validated research survivors can launch tokens through Bankr while the application exposes no wallet transfer, swap, signing, or raw-submit capability.

## Research budget

The keyless You.com MCP free profile provides `you-search` with a 100-query daily limit. The runtime enforces a persistent 50/50 allocation: up to 50 searches are reserved for the dedicated `arb` research lane and up to 50 for all other agents. Cache hits do not consume the provider budget, and retries reserve their own search slot.

## Financial results

Paper opportunities are connected to a financial-results layer that reports net P&L, return on notional, win rate, drawdown, Sharpe-like statistics, and attribution by agent and opportunity category. These are measured paper results from modeled fills, not guaranteed live returns.

## Bankr token-launch mode

Four Bankr user API keys can service the 100-agent population round-robin. Keys are read only from the host environment (`BANKR_API_KEY_1` through `BANKR_API_KEY_4`) and are never stored in git. Autonomous deployment requires both local flags `BANKR_LIVE_DEPLOY=1` and `BANKR_AUTO_DEPLOY=1`.

The launcher sends only `POST /token-launches/deploy` requests. It does not call Bankr wallet transfer, swap, sign, or submit endpoints. Launches are capped locally at one attempt per wallet per cycle and the Bankr service's wallet launch quota remains authoritative. The agent chooses a deterministic creative name/ticker and launches only after the research/validation pipeline marks the candidate as passed.

Bankr user-key token launches support Robinhood Chain by default and Base when `BANKR_DEFAULT_CHAIN=base`. Check Bankr's current API-key permissions and token-launch documentation before enabling live mode.

## Termux / Web

Designed to run on ordinary Python in Termux. A lightweight local web dashboard exposes the civilization state, agent activity, discovered opportunities, strategy leaderboard, and simulation controls.

## Architecture

- `civilizations/` — agents, personas, communication, memory, evolution, council
- `strategies/` — strategy genomes, mutation, crossover, evaluation
- `markets/` — normalized market data, arbitrage and prediction-market research interfaces
- `simulation/` — living civilization event loop
- `backtesting/` — deterministic strategy evaluation
- `risk/` — position sizing, exposure and safety gates
- `web/` — local dashboard/API
- `tests/` — automated tests

## Safety

The "mind virus" concept is implemented as bounded strategy/idea propagation: information can spread and mutate inside the simulation, but agents do not self-replicate software, deploy themselves, or bypass operator controls.

No strategy is guaranteed profitable. Performance must be demonstrated through out-of-sample testing and paper trading. Bankr live deployment is an explicit host-side opt-in and is limited to token launching; fund-moving wallet operations are not implemented by the launcher.
