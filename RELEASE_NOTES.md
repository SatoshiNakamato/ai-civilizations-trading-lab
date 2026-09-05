# Release Notes

## v0.4.0 — Civilization Runtime Release Candidate

**Date:** 2026-09-05

AEON v0.4.0 is a release-candidate milestone that stabilizes the civilization architecture and establishes extension boundaries for future market, research, evolution and execution systems.

### Highlights

- Durable civilization state snapshots provide safe persistence across process restarts.
- Bounded cross-generation memory lets civilizations retain useful history without unbounded growth.
- A bounded autonomous scheduler supports repeated civilization cycles.
- The execution layer explicitly separates paper execution from future live-exchange adapters and keeps live execution guarded by default.
- Market discovery remains provider-agnostic and supports the full discovered trading-pair universe rather than restricting civilizations to BTC, ETH or USDT-only assets.
- Audit, lineage, anti-gaming, evidence, scoring, fitness, tournament, selection, evolution and generation components are integrated into the lifecycle.
- The repository passed 164 automated tests immediately before release metadata preparation.

### Architecture policy

The core interfaces are treated as stable extension boundaries, not as a feature freeze. Future releases can add new civilizations, forecasting models, markets, providers, risk policies, evolution strategies and exchange adapters without requiring a redesign of the core lifecycle.

### Execution and security

Live trading is not enabled merely by installing AEON. Real-money execution remains behind explicit credentials, risk limits, deployment policy and human/operator controls. Secrets and private runtime state must never be committed to Git.

### Distribution

The GitHub repository is the canonical source distribution. Tagged GitHub source archives represent reproducible release snapshots and contain no private runtime state or credentials.
