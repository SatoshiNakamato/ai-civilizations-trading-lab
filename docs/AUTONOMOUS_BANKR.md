# Autonomous Bankr Launch Mode

The civilization has two classes of agents:

- **Research agents:** all configured civilization agents may generate hypotheses, debate them, verify evidence, and rank opportunities.
- **Execution agents:** `A001`–`A004` are the only agents mapped to Bankr API keys.

## Required Voroa environment variables

Set the four existing secrets:

```text
BANKR_API_KEY_1=...
BANKR_API_KEY_2=...
BANKR_API_KEY_3=...
BANKR_API_KEY_4=...
```

Then enable live autonomous token launching:

```text
BANKR_LIVE_DEPLOY=1
```

Optional fee routing to a public treasury EVM address:

```text
BANKR_FEE_RECIPIENT=0xYourPublicTreasuryAddress
```

Do **not** put API keys in GitHub files, `.env` files committed to the repository, logs, or issue comments.

## Bankr key permissions

For each A001–A004 key, use least privilege in Bankr:

- `tokenLaunchApiEnabled`: **ON**
- `walletApiEnabled`: **OFF**
- general wallet write/transfer/sign/submit access: **OFF**
- keep the key dedicated to the agent account

Token launch is an independent Bankr capability. The application only calls `POST /token-launches/deploy`.

## Autonomous launch loop

Each cycle:

1. 100 agents research independently.
2. Hypotheses are challenged by an adversarial debate pass.
3. Evidence and risk are scored.
4. Surviving opportunities are ranked.
5. A001–A004 candidates pass the deployment policy.
6. `TickerBrain` chooses a short, pronounceable, thesis-linked ticker and avoids recent public Bankr ticker collisions.
7. The chain alternates between Robinhood Chain and Base.
8. If live mode is enabled, the selected execution agent calls Bankr directly and records the returned token address and transaction hash.
9. Launch state is written to the lifecycle and Bankr audit logs.

Bankr imposes a launch quota per wallet and a minimum spacing between launches. The runtime tracks successful launches from its audit log and refuses to exceed the configured three-launch rolling-24-hour cap per agent.

## Important

A strong ticker can improve memorability and branding, but the ticker generator does **not** claim that a ticker will be profitable. Research quality, liquidity, market conditions, distribution, and user demand remain uncertain.

The worker is autonomous once hosted and `BANKR_LIVE_DEPLOY=1` is configured; no Termux wake-up is required for each cycle.
