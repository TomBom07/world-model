# Research plan

## Research question

Can a compact, self-revising mechanism learner recover the active rule of a changing reflexive system with fewer observations and better out-of-distribution behavior than conventional black-box baselines?

## Phase 0 — falsifiable mechanism sandbox ✅

Implemented:

- known hidden mechanisms
- known structural break
- sparse symbolic compiler
- MDL-style model selection
- reaction-factor tomography
- residual regime detector
- ontology-break suggestions
- prediction invariants
- adversarial perturbation search
- sample-efficiency baseline harness

## Phase 1 — strategic hidden worlds ✅

Implemented:

- heterogeneous strategic populations
- private first-order beliefs
- explicit second-order beliefs
- leverage constraints
- margin / forced-deleveraging events
- dealer hedging
- observationally similar worlds with different hidden causes
- cross-asset reaction fingerprints
- active event selection
- posterior mechanism updating
- belief-field compression
- second-order-belief ablation
- active-vs-random identification benchmark

### Phase 1 success metrics

- ordinary return-path correlation between hidden worlds
- normalized distance between observationally equivalent histories
- separability of diagnostic reaction fingerprints
- posterior mass on the true hidden mechanism
- entropy reduction
- active-event vs random-event information gain
- held-out uplift from adding second-order beliefs

## Phase 2 — sealed historical experiments 🟡 protocol implemented

The anti-leakage and evaluation protocol is implemented. Real historical datasets have **not** been used yet.

Implemented infrastructure:

- explicit per-feature availability timestamps
- fail-closed look-ahead leakage audit
- immutable train/evaluation chronology
- cryptographic experiment + dataset + forecast seals
- frozen event-level forecasting
- RMC reaction fingerprint model
- Ridge baseline
- Random Forest baseline
- MLP neural baseline
- local-level state-space baseline
- calibration / log-score / directional / error metrics
- CSV ingestion schema

Next: freeze the first real dataset schema and only then expose the evaluation period.

Freeze the architecture and hyperparameters **before** revealing later periods.

Build event-defined datasets around:

- earnings
- CPI-like inflation releases
- central-bank decisions
- liquidity / funding shocks
- large volatility events

For each event family:

1. define observable state using only information available before the event;
2. generate candidate mechanism fingerprints;
3. timestamp the candidate predictions;
4. reveal the event window;
5. update mechanism probabilities;
6. score calibration and predictive likelihood;
7. compare against simple and strong baselines.

Baselines should include linear / Ridge, tree ensembles, state-space models and at least one neural time-series model.

## Phase 3 — live paper forecasting

Timestamp every forecast before the event. No retroactive changes.

Track:

- calibration
- likelihood
- abstention quality
- regime-change detection delay
- whether active event selection improves learning
- transaction-cost-aware paper performance only as a secondary metric

## Phase 4 — open-ended mechanism invention

Permit the system to propose new variables and executable mechanisms when all current worlds fail.

A proposed ontology change must earn its place by improving out-of-sample compression / prediction, not by sounding plausible.

## Non-goals

Synthetic performance is not evidence of real-market alpha. A mechanism can be scientifically interesting without being tradeable after costs, latency, crowding and execution.

The project should prefer a falsified hypothesis over a flattering backtest.
