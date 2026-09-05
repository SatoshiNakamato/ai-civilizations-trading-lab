# Release Notes

## v0.2.0 — Endurance + Twenty-System Civilization Runtime

**Date:** 2026-09-05

AEON v0.2.0 is a release-hardening milestone for the autonomous civilization simulation.

### Highlights

- Twenty explicit civilization systems participate in the life loop: identity, needs, goals, memory, reflection, relationships, culture, organizations, economy, jobs, contracts, research, experiments, discoveries, reputation, innovation, lineage, migration, governance and endurance.
- Endurance telemetry reports current RSS separately from peak RSS and adapts the active workload under memory pressure.
- State histories are bounded and persistence is throttled during normal multi-tick operation while still forcing safe checkpoints at run boundaries and pressure events.
- Real-data market validation is used for research scoring while live execution remains disabled by default.
- Public-web research is bounded and domain-controlled; generated artifacts remain world-scoped.
- Regression coverage reaches 91 passing tests in the release validation run.

### Resource behavior

The runtime is intended to remain usable in constrained environments such as mobile/hosted workers. A long run may take materially longer when market-data requests are slow; canceling a run safely stops the current process rather than indicating a corrupted civilization state.

### Security posture

Creator control-plane commands are intentionally omitted from the public quick-start documentation. Secrets, credentials and private runtime state must never be committed to Git. Live trading remains a separate operational decision behind explicit credentials, risk limits, deployment policy and human controls.

### Distribution

The GitHub repository is the canonical source distribution. Tagged GitHub source archives should be treated as reproducible release snapshots; no private state or credentials are part of the release.
