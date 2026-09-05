# Governed Agent Communication

The civilization now has a durable inter-agent message bus at `civilizations/agent_communication.py`.

## Model

Agents do not receive raw filesystem access. They receive a narrow communication capability:

- publish a research finding, hypothesis, objection, or memory reference to another agent;
- broadcast an idea to a bounded recipient set;
- read their own inbox;
- inspect a bounded conversation between two agents.

Messages are persisted as JSONL and every publish is recorded in a separate audit log.

## Governor boundary

The communication bus enforces:

- safe agent identifiers and topics;
- per-message size limits;
- total message quotas;
- bounded broadcast fan-out;
- optional message TTL;
- durable audit records.

This gives the agents a shared memory/idea channel without giving them unrestricted access to the host filesystem or repository.

## API keys

**Do not give individual agents API keys.** The evolution governor also does not need trading credentials merely to run communication or memory operations.

If live exchange, email, GitHub, or other external capabilities are added later, the safer architecture is:

`agent -> governed capability request -> governor/policy -> credential-holding adapter -> external service`

The credential remains in the worker environment/secret store. The agent receives the result of an approved operation, not the secret itself.

For trading, keep deployment paused until the policy layer, spend limits, allowlists, duplicate-order protection, and kill switch are explicitly enabled and tested.
