# Architecture

The system is organized as a continuous decision loop:

```text
Research
  -> independent hypotheses
  -> cross-agent challenge
  -> evidence verification
  -> opportunity ranking
  -> risk governor
  -> deployment policy
  -> Bankr execution
  -> on-chain observation
  -> P&L measurement
  -> strategy evolution
  -> next research cycle
```

## Separation of responsibilities

- **Civilizations** coordinate agents, research, debate, evidence, and strategy evolution.
- **Markets** provide opportunity, execution, portfolio, deployment, observation, audit, and replay primitives.
- **Risk** decides whether a candidate is eligible for execution.
- **Simulation** owns continuous runtime, persistence, and operational visibility.

## Agent model

Each agent should maintain independent hypotheses and strategy state. Shared evidence can be verified independently so that consensus is earned rather than assumed.

## Execution boundary

Research must not directly trigger execution. Candidates pass ranking, risk, and deployment-policy gates before an execution adapter is called. This keeps live execution replaceable and auditable.

## Feedback loop

Every completed opportunity should produce an observation and measurable outcome. Strategy metrics aggregate those outcomes; strategy evolution uses the measurements to influence future research and selection.

## Persistence

Runtime state, observations, and audit information should be persisted so a hosted worker restart does not erase the civilization's operating history.
