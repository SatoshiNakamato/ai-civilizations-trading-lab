# AEON — Artificial Evolutionary Organizational Network

A research-first simulation where 100 specialized AI market intelligences become a living digital civilization.

> **Don't build agents. Build the world where they evolve.**

## What is new

AEON extends the original trading laboratory with an emergent social/economic layer. Agents do not merely generate trading ideas: they form organizations, exchange bounded strategy memes, mutate hypotheses, accumulate social capital and compete for evidence-backed influence.

The core loop is:

**Observe → Research → Hypothesize → Validate → Debate → Share → Adopt → Mutate → Organize → Evolve**

The important distinction is that the civilization is not scripted to choose a winning strategy. The simulation supplies rules, resources and feedback; strategies and organizations emerge from repeated interaction.

## Civilization primitives

- **100 agents** across quant, arbitrage, macro, momentum, value, contrarian, risk, probability, microstructure and exploration roles.
- **Strategy memes** — bounded information objects that can be adopted, challenged and mutated inside the simulation.
- **Organizations** — agents can form mission-driven guilds with members, treasury and influence.
- **Social capital** — cooperation becomes a measurable resource.
- **Discovery and innovation** — evidence-backed discoveries and mutations become civilization-level state.
- **Evidence loop** — market hypotheses remain subject to real-data validation and out-of-sample checks.
- **Trading intelligence** — arbitrage, research, prediction-market and risk modules remain available as civilization capabilities.
- **Public-web research** — agents can consume bounded public HTTPS research inputs without receiving unrestricted host access.
- **Bounded creation** — generated artifacts stay inside the civilization's world boundary.
- **Adaptive endurance** — long-running simulations monitor process memory, periodically collect garbage and reduce active workload when memory pressure rises.
- **Alert-only live boundary** — live execution remains disabled by default and is not required to run the civilization.

## Run locally

Install the dependencies and start the public web interface:

```bash
python -m pip install -r requirements.txt
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in a browser. Use the web controls to advance the civilization and observe organizations, strategy memes, research and events emerge.

For a lightweight local simulation run:

```bash
python -m civilizations.core
```

## Architecture

- `civilizations/` — agents, cognition, research, society, evolution, emergence and endurance controls
- `markets/` — normalized market data, arbitrage, prediction-market research and paper infrastructure
- `simulation/` — continuous civilization workers
- `backtesting/` — deterministic validation
- `risk/` — exposure and safety gates
- `web/` — local AEON console/API
- `tests/` — automated regression and endurance tests

## Endurance and resource limits

AEON is designed to remain usable on constrained environments. The runtime uses bounded histories, periodic garbage collection, adaptive active-agent scheduling and process-level RSS telemetry. The default endurance thresholds are intentionally below a 500 MB external runtime ceiling, leaving headroom for the host environment.

The simulation's world boundary is separate from the host operating system. World artifacts are not equivalent to arbitrary host filesystem access, and autonomous code execution is not enabled by default.

## Safety

The earlier “mind virus” concept is implemented only as bounded strategy/idea propagation. Strategy memes are data structures inside the simulation: agents do not self-replicate software, bypass permissions or execute autonomous host code.

Live trading is not implied by simulated performance. Any future execution integration must remain behind explicit credentials, risk limits, human controls and independent validation.

## Development

Run the regression suite before contributing or releasing:

```bash
python -m pytest -q
```

See `ARCHITECTURE.md`, `OPERATIONS.md`, `SECURITY.md` and `RELEASE_CHECKLIST.md` for project-level engineering and release documentation.
