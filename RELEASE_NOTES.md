# Release Notes

## v0.1.0 — Autonomous Civilization Runtime

**Date:** 2026-09-04

This release establishes the first continuous autonomous runtime for the AI Civilization Trading Lab.

### Core capabilities

1. **Agent registry** — agents can be represented independently with their own research/strategy state.
2. **Research pipeline** — agents generate independent hypotheses rather than relying on one shared thesis.
3. **Cross-agent challenge** — candidate decisions can be challenged before execution.
4. **Evidence verification** — hypotheses are scored against evidence and executionability.
5. **Opportunity ranking** — surviving opportunities are ranked for downstream decision-making.
6. **Risk governor** — execution is subject to explicit risk gates.
7. **Deployment policy** — deployment decisions are separated from research decisions.
8. **Bankr integration** — configured Bankr agents can be authenticated and selected for deployment workflows.
9. **On-chain observation** — deployment outcomes can be tracked after execution.
10. **P&L tracking** — outcomes feed portfolio and performance measurement.
11. **Strategy metrics/leaderboards** — strategy performance can be compared over time.
12. **Strategy evolution** — measured outcomes can inform future strategy selection and adaptation.

### Operations

The hosted worker runs continuously and persists runtime state under the configured data directory. Voroa can auto-deploy changes from the GitHub `main` branch.

### Security

Secrets such as Bankr API keys must remain in the host's environment/secret manager. Never commit credentials to Git.

### Known limitation

The current release is an infrastructure/runtime milestone. Live autonomous deployment should remain behind the deployment policy and risk gates until production credentials, funding, market-data quality, and operational limits are explicitly configured.
