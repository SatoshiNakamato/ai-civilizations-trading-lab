# Frontier Civilization Engine

The lab now includes a bounded multi-civilization research layer designed to make the project feel genuinely unconventional while remaining testable and safe.

## What it adds

- **Multiple civilizations:** six independent doctrines by default.
- **Idea contagion:** research hypotheses can propagate between civilizations inside the simulator.
- **Adversarial challenge:** signals are challenged before propagation and their confidence is updated.
- **Strategy mutation:** each civilization generates new doctrine mutations over time.
- **Civilization championship:** civilizations are ranked by knowledge, resilience, influence and simulated capital.
- **Economic stress testing:** paper-only shocks test which civilizations remain resilient.
- **Bounded emergence:** signal and event stores are capped to prevent runaway state growth.
- **Safety boundaries:** no real orders, external fund movement, self-replication or uncontrolled network propagation are performed by this layer.

## Runtime integration

`civilizations.core.Civilization` owns a `FrontierCivilizationEngine`. Every civilization step advances the frontier layer and exposes its state under the `frontier` key in the normal snapshot.

The result is deliberately a **laboratory for emergent coordination**, not a claim that autonomous civilizations or self-propagating software minds already exist in the real world.
