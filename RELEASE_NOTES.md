# Release Notes

## v0.5.0 — Collective Evolution Release

**Date:** 2026-09-05

AEON v0.5.0 connects the 100-agent civilization into a governed collective evolution loop. Agents can communicate, exchange research, debate hypotheses, preserve durable memories and strategies, evaluate outcomes and generate governed proposals for future improvement.

### Highlights

- Integrated the 100-agent population into recurring collective learning and research cycles.
- Added a durable inter-agent communication bus for findings, hypotheses, objections and memory references, with bounded fan-out, message limits and audit records.
- Added collective synthesis and adversarial debate so ideas can be challenged before adoption.
- Added governed persistent agent memory and world-scoped artifact creation, including nested folders for durable research and strategy records.
- Added strategy preservation, outcome feedback and genealogy so useful ideas can be carried forward and replayed across generations.
- Integrated a fifteen-stage collective evolution loop: observe, lane assignment, independent research, peer exchange, synthesis, hypothesis generation, adversarial debate, evidence verification, confidence calibration, adoption, bounded experiments, outcome evaluation, strategy feedback, genealogy and governed mutation proposal.
- Added an evolution frontier that turns strong results into explicit source-change proposals rather than allowing agents to silently mutate project code.
- Added durable collective-evolution telemetry to world snapshots for operator inspection.
- Kept GitHub persistence optional and governed: artifacts/proposals can be published to dedicated non-main evolution branches, while agents cannot independently push source changes to `main`.
- Preserved the existing notification governor, execution boundary, risk controls, endurance controls, Arena evaluation and provider-agnostic market infrastructure.
- Full local regression suite: **197 tests passing** on the release branch before publication.

### Communication and memory model

Agents communicate through a governed message bus rather than unrestricted host access. Research findings, hypotheses, objections and memory references can be exchanged between agents and incorporated into collective learning cycles.

Agents can create durable memory and research artifacts only through the Evolution Governor's world-scoped namespaces. Writes are subject to path-safety, file-size, total-storage and file-count limits and are recorded in an append-only audit trail.

The system therefore supports persistent machine-to-machine learning without giving individual agents unrestricted filesystem, repository, source-code or deployment authority.

### Autonomous evolution boundary

The strongest collective results may produce governed mutation proposals. A proposal is evidence for human review, not an autonomous source-code modification. Optional GitHub persistence is restricted to governed artifact/document/proposal namespaces and dedicated non-main branches.

No API key is required for the local collective evolution loop. External credentials remain in the worker/secret environment and should be accessed only through governed capability adapters. Agents should never receive raw trading, GitHub administration, secret-management or workflow-modification credentials.

### Execution and security

Live trading is not enabled merely by installing AEON. Real-money execution remains behind explicit credentials, risk limits, deployment policy, duplicate-order protection, kill-switch controls and human/operator approval.

Secrets and private runtime state must never be committed to Git.

### Validation

The release branch includes automated coverage for communication, collective learning, evolution frontier behavior and the fifteen-stage collective evolution loop. The full local regression suite passed 197 tests during release preparation.

### Distribution

The GitHub repository is the canonical source distribution. Tagged GitHub source archives represent reproducible release snapshots and contain no private runtime state or credentials.

## v0.4.0 — Civilization Runtime Release Candidate

**Date:** 2026-09-05

AEON v0.4.0 established the stabilized civilization architecture and extension boundaries for market, research, evolution and execution systems.

### Highlights

- Durable civilization state snapshots provide safe persistence across process restarts.
- Bounded cross-generation memory lets civilizations retain useful history without unbounded growth.
- A bounded autonomous scheduler supports repeated civilization cycles.
- The execution layer explicitly separates paper execution from future live-exchange adapters and keeps live execution guarded by default.
- Market discovery remains provider-agnostic and supports the full discovered trading-pair universe rather than restricting civilizations to BTC, ETH or USDT-only assets.
- Audit, lineage, anti-gaming, evidence, scoring, fitness, tournament, selection, evolution and generation components are integrated into the lifecycle.

## v0.2.0 — Release hardening

- Twenty civilization systems are integrated into the autonomous life loop.
- Endurance controls track current and peak RSS separately and adapt workload under pressure.
- Bounded histories, persistence throttling and memory-pressure handling reduce long-run growth.
- Public-web access is bounded and domain-controlled.
- World-scoped artifact creation and execution-disabled-by-default boundaries remain enforced.
- Research, validation, paper-trading and risk-governor infrastructure remain available without requiring funded live execution.

## v0.1.0 — Initial civilization runtime

- Continuous civilization runtime.
- Independent agent research and hypothesis scoring.
- Cross-agent challenge and evidence verification components.
- Opportunity ranking and risk governor.
- Deployment policy and Bankr agent integration scaffolding.
- Portfolio, audit, observation, stale-data, replay, and strategy metrics infrastructure.
- Persistent simulation state and dashboard primitives.
