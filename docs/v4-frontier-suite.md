# V4 — Frontier discovery suite

V4 turns the remaining WorldModel research roadmap into one executable falsification
suite. The goal is not to claim that autonomous science is solved. The goal is to make
the hard claims concrete enough that they can fail.

## What V4 adds

### Nonlinear ontology discovery

V3 learned causal coordinates in a linear observation space. V4 lifts observations
into a random Fourier feature space and then finds canonical directions aligned with
known intervention descriptors.

For observation features (phi(x)) and interventions (u), the learner searches for
directions with large whitened cross-covariance:

[
W_x ; mathrm{Cov}(phi(x),u) ; W_u
]

The canonical correlations are compared against shuffled-intervention null
distributions. Latent dimensions are kept only when they beat that null.

That means the number of latent coordinates is no longer supplied by hand in the
frontier benchmark.

### Joint ontology + law discovery

A latent state is only useful if simple laws can be written in it.

V4 compiles transition laws of the form

[
Delta z_t = f(z_t, u_t)
]

with the symbolic mechanism compiler. Candidate ontology sizes are compared using
held-out transition error, description-length pressure and intervention alignment.

### Open-world theory invention

If all known theories fail, V4 no longer stops at `__unknown__`.

It models the systematic residual left by the incumbent theory and compiles a compact
symbolic correction. The proposed new theory must then improve a holdout set before it
is accepted.

The frontier test deliberately omits an interaction mechanism from the incumbent
family. The system must:

1. move posterior mass to `__unknown__`;
2. propose a new symbolic correction;
3. recover the missing interaction;
4. improve holdout error.

### Natural experiments

When intervention labels do not exist, WorldModel can propose candidate environments
from blockwise distribution shifts. These labels are hypotheses about natural
experiments, not causal ground truth.

### Ontology evolution

WorldModel now has explicit split/merge proposals:

- **split** a coordinate when a simple partition explains systematic residual structure;
- **merge** coordinates when they are nearly redundant.

This is the first executable version of an ontology changing its vocabulary rather
than only changing coefficients.

### Performative / reflexive experiment design

Expected information gain already rewards informative observations. V4 additionally
penalizes probes whose publication or execution has strong feedback on the world.

A useful experiment can therefore lose to a slightly less informative probe when the
first probe would substantially alter the process being measured.

### Prospective falsification registry

Predictions can be sealed before a future event and scored only after the event time.
The seal covers the prediction payload and detects tampering.

Historical replay remains useful, but prospective claims are the stronger standard.

## Unified objective

V4 includes a first explicit **Falsifiable Causal Compression** objective.

Lower is better:

[
mathcal{J} =
log L_{mathrm{pred}}
+ lambda C
+ alpha I_{mathrm{inv}}
+ eta I_{mathrm{cal}}
+ gamma H(Mmid D)
- eta mathrm{EIG}(q)
+ ho mathrm{Cost}(q)
+ psi mathrm{Feedback}(q)
+ kappa P(M_{mathrm{unknown}})
]

It rewards:

- predictive adequacy;
- short executable explanations;
- invariance;
- calibration;
- reduction of unresolved uncertainty;
- informative falsification opportunities;

and penalizes:

- unnecessary complexity;
- expensive experiments;
- performative feedback;
- evidence that the current model family is misspecified.

This is a research objective, not a theorem that these weights are universally optimal.

## Frontier benchmark

Run:

```bash
worldmodel frontier --seed 7
```

The suite tests:

- nonlinear latent recovery in physics-like, ecology-like and epidemic-like worlds;
- automatic latent dimension selection;
- unlabeled natural-regime discovery;
- symbolic recovery of Hénon-map dynamics;
- joint controlled ontology + law discovery;
- rejection of an incomplete hypothesis family;
- invention of a missing interaction mechanism;
- ontology split and merge pressure;
- feedback-aware experiment choice;
- prospective sealing and time-order enforcement;
- unified-objective directionality.

CI runs the frontier suite across multiple seeds.

## Scientific boundary

Passing V4 means the architecture survives a substantially harder collection of
controlled tests. It still does **not** show that WorldModel has discovered a new law
of nature, a new economic mechanism, or a new biological mechanism.

The next evidence threshold is external and prospective:

1. freeze the architecture and benchmark before looking at outcomes;
2. use a real intervention or natural experiment;
3. preregister the representation, mechanisms and reaction predictions;
4. collect the outcome after the seal;
5. compare against strong domain baselines;
6. replicate in a second domain without retuning the discovery rules.

A real breakthrough begins when the machine proposes a mechanism humans did not put
into the candidate set and that mechanism survives a genuinely new experiment.
