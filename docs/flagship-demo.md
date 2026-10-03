# Flagship demo: The Hidden World Lab

The flagship demo is the shortest path from “I opened the repo” to understanding why WorldModel is different.

## Goal

In under 60 seconds, show a machine doing something qualitatively more interesting than curve fitting:

1. observe data compatible with multiple explanations;
2. construct or receive competing executable worlds;
3. show that ordinary observations cannot distinguish them;
4. search possible probes;
5. select the probe with maximum expected discrimination;
6. preregister each world's reaction fingerprint;
7. reveal the observation;
8. update posterior belief;
9. reveal hidden ground truth to the evaluator;
10. score whether the true mechanism was identified.

## Required visual sequence

### Scene 1 — Same evidence

Two lines almost overlap.

Label:

> Same history. Different causes.

Do not reveal which world is true.

### Scene 2 — Competing explanations

Show two compact world cards.

**Belief world**
- second-order beliefs dominate;
- participants react to expected reactions of others.

**Liquidity world**
- leverage and balance-sheet constraints dominate;
- forced deleveraging and dealer hedging amplify shocks.

The point is not finance. The point is observational equivalence.

### Scene 3 — Ask reality a better question

Display candidate probes ranked by information score.

Headline:

> What should we observe next?

The selected probe should visibly separate the predicted fingerprints of the two worlds.

### Scene 4 — Commit before seeing the answer

Freeze both predicted fingerprints before revealing the synthetic outcome.

This is essential. It turns the demo from storytelling into a test.

### Scene 5 — Reality answers

Animate the observed fingerprint over the preregistered alternatives.

Show the posterior moving from uncertainty toward one world.

### Scene 6 — Reveal the hidden world

Only now reveal the simulator's hidden truth.

Show:
- predicted mechanism;
- true mechanism;
- entropy reduction;
- selected-probe information score;
- whether identification succeeded.

## Success criteria

The default seeded demo should satisfy all of the following:

- pre-probe histories are strongly observationally similar;
- prior uncertainty is non-trivial;
- the active probe scores higher than a random probe;
- the predicted fingerprints visibly differ;
- the posterior moves materially after one diagnostic observation;
- the ground-truth mechanism is recoverable more often with active selection than random selection across many seeds.

Do not hand-pick a single lucky seed as scientific evidence. The pretty default seed is a product demo; the multi-seed benchmark is the evidence.

## Second flagship demo

After the market world is stable, add a completely different synthetic domain using the same engine.

Good candidates:
- coupled physical system with an unobserved force;
- epidemic with two observationally equivalent transmission mechanisms;
- ecological predator/prey system with a hidden seasonal driver;
- game environment with a latent rule switch.

The purpose is to prove **domain transfer of the discovery loop**, not to add another dashboard.

## The shareable sentence

> Two worlds explain the past equally well. WorldModel figures out what to observe next to discover which one is real.
