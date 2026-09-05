# AEON — Artificial Evolutionary Organizational Network

**Release: v0.4.0**

A research-first simulation where 100 specialized AI market intelligences become a living digital civilization.

> **Don't build agents. Build the world where they evolve.**

**Project:** [@aeongithub](https://x.com/aeongithub)  
**Creator:** [@royaltheose](https://x.com/royaltheose)

**Project enquiries:** iNeed2p@wearehackerone.com

## Unreleased — next release candidate

The current `main` branch contains the next notification-governance and CI work. **It is not released or tagged yet.** A release tag will only be created after explicit release confirmation.

Planned release work includes:

- **Notification Governor** — critical/high/info alerts are fingerprinted, deduplicated and rate-limited before delivery.
- **Durable notification state** — send counts, dedupe fingerprints and SMTP circuit state survive worker restarts.
- **SMTP quota protection** — provider throttling such as Gmail `550 5.4.5` opens a persistent circuit until the next local day instead of producing repeated hot-loop failures.
- **Provider isolation** — notification delivery remains behind a small boundary so SMTP/provider failures cannot crash the civilization worker.
- **Deterministic fingerprints** — identical alert content produces the same stable fingerprint across runs.
- **Hermetic CI** — tests do not depend on Binance public API availability; market-dependent tests use deterministic fixtures.
- **Reproducible test environment** — CI fixes the runner image, Python patch version, locale/timezone, hash seed and pytest version.

This work separates two concerns that previously collided in production: **finding opportunities** and **deciding whether the operator should be interrupted about them**.

## Civilization Arena

AEON includes an objective Civilization Arena for evaluating evolving civilizations against independently supplied outcomes rather than allowing the simulation to grade itself.

The Arena records immutable forecast commitments, accepts externally sourced outcomes, calculates deterministic probabilistic scores and ranks civilizations only when enough resolved observations exist. This creates an explicit selection pressure for accuracy, calibration and reproducibility instead of rewarding unsupported claims of profitability.

The Arena is provider-agnostic so external outcome evaluators can be connected without coupling the civilization engine to a single service. Forecasts are committed before resolution, and resolved outcomes cannot be silently replaced.

## Civilization systems

AEON wires twenty explicit civilization systems into the life loop:

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
- **Civilization Arena** — forecasts can be committed and evaluated against externally supplied outcomes with deterministic scoring and lineage-safe rankings.
- **Trading intelligence** — arbitrage, research, prediction-market and risk modules remain available as civilization capabilities.
- **Public-web research** — agents can consume bounded public HTTPS research inputs without unrestricted host access.
- **Alert governance** — high-value findings can pass through a notification governor before external delivery.
- **Bounded creation** — generated artifacts stay inside the civilization's world boundary.
- **Alert-only live boundary** — live execution remains disabled by default and is not required to run the civilization.

## Governed autonomous evolution

AEON now has a dedicated **Evolution Governor** for the next level of agent autonomy: agents can create persistent memory, research artifacts and evolution proposals without receiving unrestricted host or repository control.

The boundary has three layers:

1. **Agent workspace** — agents may create files and nested folders only inside governed namespaces such as `world_artifacts/agent_memory/<agent>/`.
2. **Governor** — every write is checked for path traversal, symlinks, per-file bytes, total storage and file-count quotas and is recorded in an append-only audit log.
3. **Promotion boundary** — source-code changes are proposals, not direct source writes. An optional GitHub publisher can persist governed artifacts to a dedicated `aeon/agent-memory-*` branch; it cannot publish to `main` and it rejects source namespaces.

This creates a useful form of machine evolution: the civilization can accumulate its own memory, preserve discoveries, form hypotheses about how it should improve and leave durable artifacts for later generations. The project remains human-reviewable because source mutation and production execution stay outside the agent's authority.

### Optional GitHub persistence

Set these only in the hosted worker environment, never inside repository files:

- `AEON_GITHUB_TOKEN` — a GitHub fine-grained token with the minimum repository Contents permission needed for the dedicated branch workflow.
- `AEON_GITHUB_REPO` — defaults to `SatoshiNakamato/ai-civilizations-trading-lab`.
- `AEON_GITHUB_BASE_BRANCH` — defaults to `main`.

The runtime should publish a batch after a cycle rather than letting 100 agents independently push. This gives the governor one auditable promotion point and avoids branch/commit storms.

**Important:** do not give an agent a token that can administer the repository, manage secrets, alter workflows or bypass branch protection. The autonomy model is intentionally powerful inside its workspace and deliberately weak at the project-control boundary.

## Notification governance

AEON treats operator notifications as a scarce resource rather than an unbounded side effect.

The `NotificationGovernor` applies three controls before delivery:

1. **Fingerprinting** — identical severity/subject/body combinations map to a deterministic identifier.
2. **Deduplication** — repeated copies of the same alert are suppressed during the configured dedupe window.
3. **Rate limiting** — the number of outbound notifications is capped inside the configured cycle and daily limits.
4. **Durable circuit breaking** — provider quota failures are persisted so restarting the worker does not immediately retry the same exhausted SMTP quota.

Delivery errors are contained. A provider-side quota/throttle failure returns a degraded result to the caller instead of causing the autonomous worker to repeatedly fail and restart. The governor is deliberately provider-agnostic, allowing Voroa/SMTP today and another notification provider later.

For trading alerts, notification is an **observation channel**, not an execution permission. A message about an arbitrage or token opportunity does not authorize a live order.

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

- `civilizations/` — agents, cognition, research, society, evolution, emergence, world dynamics, endurance controls, Arena evaluation and notification governance
- `markets/` — normalized market data, arbitrage, prediction-market research and paper infrastructure
- `simulation/` — continuous civilization workers
- `backtesting/` — deterministic validation
- `risk/` — exposure and safety gates
- `execution/` — guarded order submission boundary
- `web/` — local AEON console/API
- `tests/` — automated regression, system-integration, Arena, endurance and notification-governance tests
- `.github/workflows/` — deterministic, hermetic CI

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

The test suite is intentionally hermetic: tests that exercise civilization steps use deterministic market fixtures instead of depending on live exchange availability. Live-market integration belongs in explicit integration/evaluation environments.

See `ARCHITECTURE.md`, `OPERATIONS.md`, `SECURITY.md` and `RELEASE_CHECKLIST.md` for project-level engineering and release documentation.

## License

AEON is source-available with **all rights reserved**. The source is publicly viewable for research, evaluation and educational inspection, but copying, modification, redistribution, sublicensing, publication or commercial/derivative use is not granted without prior written permission from the copyright holder.

See [`LICENSE`](LICENSE) for the full terms.
