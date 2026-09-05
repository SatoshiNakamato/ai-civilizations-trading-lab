# Collective Evolution — 15 Stages

The V5 frontier now runs one governed collective-learning cycle per world tick.
The implementation composes the existing communication bus, collective-learning
layer, evolution frontier, civilization platform, and evolution governor rather
than creating duplicate research or debate systems.

## The fifteen stages

1. **Observe** — normalize the evidence produced by the population.
2. **Assign lanes** — distribute bounded research, challenge, and experiment roles.
3. **Independent research** — preserve each agent's own observation before sharing.
4. **Peer exchange** — exchange evidence through the durable communication bus.
5. **Synthesize** — compute a collective summary and source diversity.
6. **Generate hypotheses** — turn shared findings into testable proposals.
7. **Adversarial debate** — request counter-evidence and reproducible tests.
8. **Verify evidence** — reject empty or low-confidence claims.
9. **Calibrate confidence** — discount confidence when evidence has not survived challenge.
10. **Select adoptions** — adopt only claims passing the existing threshold.
11. **Run experiments** — test selected ideas inside the bounded civilization platform.
12. **Evaluate outcomes** — measure experiment score and repeatability.
13. **Adapt strategies** — feed outcomes back into simulated agent knowledge.
14. **Record genealogy** — preserve who influenced which adopted idea.
15. **Propose governed mutation** — create a source-change proposal for review.

## Safety boundary

The loop does **not** grant agents repository credentials, arbitrary filesystem
access, unrestricted execution, or automatic source-code writes. Stage 15 ends
at a governed proposal. The existing evolution governor remains the authority
boundary for persistent artifacts and source-change proposals.

The world snapshot exposes `collective_evolution` and
`collective_evolution_loop` so operators can inspect every stage and cycle
without reading the communication log directly.
