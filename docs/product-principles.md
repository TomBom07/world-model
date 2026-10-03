# Product and build principles

WorldModel should feel simple on the surface and rigorous underneath.

These principles are intentionally designed to keep a one-person, AI-assisted research project buildable without turning it into a pile of demos.

## 1. One sentence before one paper

A stranger should understand the project before learning any terminology:

> WorldModel builds competing explanations of a world and searches for the observation that can prove them wrong.

Technical names such as RMC, active identification, ontology revision and belief tomography belong one layer deeper.

## 2. Demo the loop, not the feature list

The primary demo must visibly show:

```text
same evidence
    ↓
competing worlds
    ↓
different future reactions
    ↓
chosen diagnostic observation
    ↓
one theory loses
    ↓
world model updates
```

A visitor should not need to read the architecture document to see why the system is unusual.

## 3. Reuse infrastructure aggressively

Novelty belongs in the research loop, not in rebuilding solved infrastructure.

Prefer proven libraries for:
- optimization;
- probabilistic inference;
- symbolic algebra;
- storage;
- visualization;
- APIs;
- experiment tracking;
- model serving.

Write custom code where it creates scientific leverage:
- executable mechanism search;
- hypothesis competition;
- active diagnostic selection;
- regime / ontology revision;
- falsification;
- evaluation of mechanism recovery.

## 4. Keep the hidden truth measurable

Synthetic environments are not toy work when they answer a question real historical data cannot:

> Did the system recover the actual generating mechanism?

Every synthetic world should expose ground truth to the evaluator but not to the learner.

## 5. Prefer one impossible-looking proof over ten weak demos

The flagship experiment should create the reaction:

> “It had multiple plausible explanations, designed its own discriminating test, then changed its theory after seeing the result.”

New features should strengthen that moment before broadening the product.

## 6. AI writes quickly; the repository remembers slowly

AI-assisted implementation should be constrained by:
- small modules;
- explicit interfaces;
- tests around scientific invariants;
- frozen experiment protocols;
- versioned datasets;
- readable docs;
- commits that explain intent.

Fast generation is useful only when the project remains auditable.

## 7. Do not claim discovery without a falsifiable benchmark

The project should distinguish:
- **implemented capability**;
- **synthetic evidence**;
- **historical evidence**;
- **speculative research target**.

“Interesting architecture” is not a breakthrough. A claim earns weight only when an experiment could have shown it to be false.

## 8. Build vocabulary people can remember

Canonical product language:

- **World** — an executable explanation.
- **Twin worlds** — different mechanisms that fit the same observations.
- **Probe** — an observation/intervention chosen to separate worlds.
- **Fingerprint** — predicted reaction under a probe.
- **Destroyer** — a counterfactual that exposes a theory's weakness.
- **Break** — evidence the current mechanism stopped working.
- **Revision** — a structural change to the internal explanation.

The vocabulary should remain stable across the UI, CLI, README and papers.

## 9. Optimize for forkability

A researcher should be able to add a new world without understanding the entire repository.

The long-term extension boundary should be:

```python
class World:
    def observe(...): ...
    def propose_probes(...): ...
    def react(...): ...
    def reveal_truth_to_evaluator(...): ...
```

The exact API can evolve, but adding a domain should not require rewriting the engine.

## 10. The project story and research story must agree

Marketing can simplify the language, never the evidence.

The homepage can say:

> Discover the rules.

The research report must still say exactly which rules were searched, which baselines were used, what data the learner saw, and where it failed.
