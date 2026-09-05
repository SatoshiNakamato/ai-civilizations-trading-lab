# AEON — Artificial Evolutionary Organizational Network

**Release: v0.2.0**

A research-first simulation where 100 specialized AI market intelligences become a living digital civilization.

> **Don't build agents. Build the world where they evolve.**

**Project:** [@aeongithub](https://x.com/aeongithub)  
**Creator:** [@royaltheose](https://x.com/royaltheose)

**Project enquiries:** iNeed2p@wearehackerone.com

## What is new

AEON combines individual cognition with an emergent social/economic layer. Agents form organizations, exchange bounded strategy memes, mutate hypotheses, accumulate social capital, research the public web, create world-scoped artifacts and compete for evidence-backed influence.

The core loop is:

**Observe → Research → Hypothesize → Validate → Debate → Share → Adopt → Mutate → Organize → Evolve**

The civilization is not scripted to choose a winning strategy. The simulation supplies rules, resources and feedback; strategies and organizations emerge from repeated interaction.

## Civilization systems

AEON now wires twenty explicit civilization systems into the life loop:

1. identity and individuality
2. needs and wellbeing
3. adaptive goals
4. bounded memory
5. reflection
6. relationships and trust
7. culture and norms
8. organizations
9. economy and prices
10. jobs and rewards
11. contracts
12. research and learning
13. experiments
14. discoveries
15. reputation
16. innovation and artifacts
17. lineage/succession markers
18. migration between world locations
19. adaptive governance
20. endurance and bounded resource usage

These are simulation mechanisms, not a claim of literal consciousness or sentience.

## Research and trading intelligence

- **100 agents** across quant, arbitrage, macro, momentum, value, contrarian, risk, probability, microstructure and exploration roles.
- **Strategy memes** — bounded information objects that can be adopted, challenged and mutated inside the simulation.
- **Evidence loop** — hypotheses remain subject to real-data validation and out-of-sample checks.
- **Trading intelligence** — arbitrage, research, prediction-market and risk modules remain available as civilization capabilities.
- **Public-web research** — agents can consume bounded public HTTPS research inputs without unrestricted host access.
- **Bounded creation** — generated artifacts stay inside the civilization's world boundary.
- **Alert-only live boundary** — live execution remains disabled by default and is not required to run the civilization.

## Run locally

Install dependencies and start the public web interface:

```bash
python -m pip install -r requirements.txt
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in a browser. Use the web controls to advance the civilization and observe organizations, strategy memes, research and events emerge.

For a lightweight local simulation run:

```bash
python -m civilizations.core
```

## Runtime architecture

The autonomous civilization worker is separated from the Creator control plane. The worker owns the live world loop, persists bounded state and continues operating when a control session disconnects or is closed. Control-plane requests are passed to the worker through a small local command queue, so observing or talking to the civilization does not stop its ongoing evolution.

The worker uses a PID guard to avoid accidental duplicate runtimes and writes diagnostic output to the local world-state area. An explicit shutdown request is required to stop the autonomous worker.

## Architecture

- `civilizations/` — agents, cognition, research, society, evolution, emergence, world dynamics and endurance controls
- `markets/` — normalized market data, arbitrage, prediction-market research and paper infrastructure
- `simulation/` — continuous civilization workers
- `backtesting/` — deterministic validation
- `risk/` — exposure and safety gates
- `web/` — local AEON console/API
- `tests/` — automated regression, system-integration and endurance tests

## Endurance and constrained environments

AEON is designed for constrained mobile/hosted environments. The runtime measures **current** process RSS on Linux/Android through `/proc/self/status` instead of treating `ru_maxrss` as current memory. Peak process RSS is retained separately for diagnostics.

When a Linux cgroup is available, the endurance layer also observes current cgroup memory. This gives hosted environments such as Voroa an early warning signal for platform-level memory pressure even when the Python process itself reports a much smaller RSS. The scheduler reacts to the larger observed value before the external 500 MB ceiling is reached.

The runtime uses bounded histories, periodic garbage collection, adaptive active-agent scheduling and reduced persistence frequency during normal operation. Default thresholds remain below a 500 MB external runtime ceiling, leaving headroom for the host environment.

## Safety

The earlier “mind virus” concept is implemented only as bounded strategy/idea propagation. Strategy memes are data structures inside the simulation: agents do not self-replicate software, bypass permissions or execute autonomous host code.

Live trading is not implied by simulated performance. Any future execution integration must remain behind explicit credentials, risk limits, human controls and independent validation.

## Development

Run the regression suite before contributing or releasing:

```bash
python -m pytest -q
```

See `ARCHITECTURE.md`, `OPERATIONS.md`, `SECURITY.md` and `RELEASE_CHECKLIST.md` for project-level engineering and release documentation.

## License

AEON is source-available with **all rights reserved**. The source is publicly viewable for research, evaluation and educational inspection, but copying, modification, redistribution, sublicensing, publication or commercial/derivative use is not granted without prior written permission from the copyright holder.

See [`LICENSE`](LICENSE) for the full terms.
