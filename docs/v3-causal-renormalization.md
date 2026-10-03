# V3 — Causal renormalization research alpha

V3 moves WorldModel from *mechanism search over hand-given variables* toward
*ontology discovery*: learning which low-dimensional coordinates are worth treating
as scientific variables.

## Research claim

The first falsifiable claim is deliberately narrow:

> When high-dimensional observations contain large environment-independent nuisance
> variation, an intervention-aware coarse-graining should recover the
> intervention-relevant latent subspace better than variance-only compression.

This is not a claim that arbitrary causal variables can already be recovered from raw
reality. The current implementation uses a transparent generalized eigenproblem so
that failure modes are inspectable.

## Components

### 1. Causal ontology learner

Given observations x and environment/intervention labels e, the learner compares:

- variation of environment means;
- variation remaining inside each environment.

It solves a whitened generalized eigenproblem that emphasizes directions with high
between-environment signal and low within-environment noise.

The result is a learned map

    x -> z

where z is a candidate causal macro-coordinate system.

### 2. Expected-information-gain experiment design

Instead of scoring a probe only by pairwise distance between predicted fingerprints,
V3 estimates expected posterior entropy after the observation:

    IG(q) = H(M | D) - E_y[H(M | D, y, q)]

Queries can later include explicit cost, risk and performative-feedback penalties.

### 3. Open-world Bayes

Closed-world inference always chooses one known model. V3 adds an explicit
none-of-the-above hypothesis:

    M_unknown

Known mechanisms use a narrow Gaussian observation model. The unknown hypothesis uses
a broader heavy-tailed likelihood, so sufficiently incompatible evidence can move
posterior mass away from every known theory.

### 4. Scientific claim sealing

A scientific claim can be frozen together with:

- code reference;
- data cutoff;
- learned ontology summary;
- candidate hypotheses;
- posterior;
- selected query;
- preregistered predictions;
- evaluation protocol.

The canonical payload receives a SHA-256 seal. This extends the V2 replay discipline
from forecasts to mechanism-level scientific claims.

## OpenMechanismBench alpha

Run:

    worldmodel breakthrough --seed 7

The alpha benchmark contains:

1. a hidden two-dimensional causal state;
2. a random high-dimensional observation mixing;
3. strong nuisance variance unrelated to intervention;
4. an intervention-aware ontology learner;
5. a PCA baseline;
6. a diagnostic-vs-ambiguous experiment-design test;
7. a familiar-vs-alien open-world test;
8. a scientific claim seal.

The benchmark intentionally exposes hidden ground truth only to the evaluator.

## What success means

A passing alpha run means the implementation supports the intended research loop and
survives this controlled falsification task.

It does **not** mean:

- causal ontology discovery is solved in general;
- the learned coordinates are uniquely identifiable;
- the method works for arbitrary nonlinear observation maps;
- real economic mechanisms have been discovered;
- the system has predictive trading edge.

## Next hard tests

1. Nonlinear hidden coordinate maps.
2. Temporal mechanism discovery after ontology induction.
3. Mechanism-family holdout: evaluation on a family absent from training.
4. Unknown-number-of-latents model selection.
5. Hierarchical split/merge ontologies.
6. Natural experiments without intervention labels.
7. Perturbational biology data.
8. Prospective sealed macro/event studies.
9. Reflexive environments where publishing the prediction changes agent behavior.

The project should only claim a stronger capability after it passes the corresponding
sealed benchmark.
