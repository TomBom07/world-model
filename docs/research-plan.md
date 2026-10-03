# Research plan

## Research question

Can a compact, self-revising mechanism learner recover the active rule of a changing reflexive system with fewer observations and better out-of-distribution behavior than conventional black-box baselines?

## Phase 0 — falsifiable sandbox

Implemented now:

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

### Success metrics

- term-level mechanism recovery
- holdout MAE
- regime-break localization error
- calibration/model-consensus behavior
- sample-efficiency curves

## Phase 1 — harder synthetic worlds

Add strategic agent populations, leverage constraints, dealer hedging, information asymmetry and explicit higher-order beliefs. The simulator should be able to produce the same price path from different hidden causes so identification is genuinely difficult.

## Phase 2 — sealed historical experiments

Freeze architecture and hyperparameters before revealing later time periods. Use event-defined datasets such as earnings, CPI, FOMC and liquidity shocks plus cross-asset reaction fingerprints. Compare against linear, tree, state-space and neural baselines.

## Phase 3 — live paper forecasting

Timestamp every prediction before the event. No retroactive changes. Track calibration, abstention quality and whether model-disagreement gates prevent bad predictions.

## Phase 4 — active world identification

Given several plausible mechanisms, choose the future observation or event whose reaction fingerprints would maximally distinguish them. The objective is not just to forecast, but to learn which world we are in.

## Non-goal

Synthetic performance is not evidence of real-market alpha. A mechanism can be scientifically interesting without being tradeable after costs, latency, crowding and execution.
