# Operations Guide

## Hosted worker

Start command:

```bash
python -m simulation.run
```

The worker is designed to remain alive, run repeated cycles, persist state, and recover from individual cycle errors.

## Environment

Keep credentials in the hosting provider's environment-variable/secret store. Never commit `.env` files or real API keys.

Suggested variables include:

```text
BANKR_API_KEY_1
BANKR_API_KEY_2
BANKR_API_KEY_3
BANKR_API_KEY_4
```

Additional market-data or notification credentials should follow the same rule.

## Deployment controls

Use the deployment policy/risk governor as the execution boundary. Keep live deployment disabled while validating new strategies, market feeds, or adapters.

## Monitoring

Monitor:

- worker uptime and cycle status;
- research and verification counts;
- ranked opportunities;
- risk approvals/rejections;
- deployment attempts/results;
- on-chain observations;
- realized/unrealized P&L;
- strategy performance;
- repeated exceptions and stale data.

## Recovery

A cycle-level exception should not terminate the worker. Investigate repeated errors from runtime logs, fix the underlying component, and allow the hosting provider to redeploy from `main`.
