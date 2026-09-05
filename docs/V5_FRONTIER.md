# V5 Frontier Evolution

The V5 frontier connects the existing civilization primitives into one governed evolution loop.

## Cycle

1. 100 agents generate or retain research evidence.
2. The communication bus exchanges observations between agents.
3. Collective learning scores adoption and runs adversarial debate.
4. Durable research memories are written through `EvolutionGovernor`.
5. Experiments and genealogy are recorded as replayable frontier events.
6. Periodically, the strongest collective result creates a **source-change proposal**.
7. Proposals are stored under the governed proposal namespace and explicitly require human review.
8. The command snapshot exposes constitution, diagnostics, collective learning, and replay paths.

## Safety boundary

Agents do not receive unrestricted filesystem, Git, source-code, trading, or deployment authority. The governor enforces namespaces and quotas. GitHub persistence, when configured, is limited to governed memory/proposal/document artifacts and a non-main evolution branch.

No API key is required for the local evolution loop. Market/exchange credentials remain separate from agent creativity and are only needed for explicitly enabled external integrations.

## Manual validation

Run the full test suite after pulling the branch:

```bash
cd ~/ai-civilizations-trading-lab
python -m pytest -q
```

Then exercise a short runtime cycle in the normal worker environment and inspect `data/evolution/` plus the `world_state/latest.json` frontier snapshot. Do not enable live trading merely to validate the evolution layer.
