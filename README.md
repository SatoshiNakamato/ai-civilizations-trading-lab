# AI Civilizations Trading Lab

A research-first multi-agent market intelligence system: 100 simulated AI civilizations with distinct personas, expertise, risk preferences, communication, strategy evolution, arbitrage research, prediction-market analysis, and cooperative portfolio intelligence.

## Vision

The civilization behaves like a society of specialized researchers. Agents observe markets, form hypotheses, debate, share strategy memes, mutate and recombine ideas, run experiments, and learn from measured outcomes. The shared objective is to improve risk-adjusted performance while preserving capital.

This project starts in simulation and paper trading. Live execution is deliberately separated behind risk controls and explicit configuration.

## Termux / Web

Designed to run on ordinary Python in Termux. A lightweight local web dashboard will expose the civilization state, agent activity, discovered opportunities, strategy leaderboard, and simulation controls.

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

No strategy is guaranteed profitable. Performance must be demonstrated through out-of-sample testing and paper trading before any consideration of live execution.
