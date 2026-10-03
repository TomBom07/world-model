# RMC architecture

WorldModel treats forecasting as **mechanism inference under reflexivity**.

## V0 — executable mechanism layer

1. Observe an event/reaction vector.
2. Compile compact mechanisms from a small symbolic language.
3. Maintain multiple alternatives using description-length scores.
4. Detect structural failure when residuals shift.
5. Search residual structure for missing interactions.
6. Reconstruct latent reaction factors.
7. Search for predictions that survive model disagreement.
8. Attack conclusions with counterfactual perturbations.

## V1 — strategic hidden-world layer

V1 adds a second representation of the world: populations with different information, objectives and constraints.

### Populations

- fundamental funds
- macro funds
- momentum
- retail
- leveraged funds
- dealers

Each population carries:

- first-order belief: its estimate of the asset/world state;
- second-order belief: its estimate of the market consensus / what others are likely to believe;
- demand rule;
- leverage state;
- population weight.

Dealers additionally carry a hedging response. Leveraged funds can be forced to deleverage when losses or liquidity stress cross a threshold.

### Observational equivalence

The simulator contains two hidden mechanisms whose normal price histories are intentionally very similar:

```text
belief_reflexive
    higher weight on beliefs about others
    lower liquidity / leverage sensitivity

liquidity_reflexive
    lower higher-order-belief weight
    stronger liquidity, leverage and dealer-hedging channel
```

A learner cannot simply inspect the price path and declare the cause.

### Active identification

For every candidate future event (e), each hidden-world hypothesis predicts a reaction fingerprint:

```text
R_M(e) =
[growth equity,
 value equity,
 two-year yield,
 volatility]
```

The identifier scores an event by how far apart the candidate fingerprints are relative to observation noise.

```text
candidate worlds
      │
      ├── predict reaction to growth shock
      ├── predict reaction to inflation shock
      ├── predict reaction to liquidity shock
      └── ...
      │
      ▼
choose highest-separation event
      │
      ▼
pre-register fingerprints
      │
      ▼
observe event reaction
      │
      ▼
Bayes-style posterior update
```

In a real market the system would not create the event. It would identify which naturally occurring scheduled or unscheduled event is most informative and pre-register predictions before observing it.

## Belief field

First-order beliefs, second-order beliefs, disagreement and the second-minus-first gap are compressed into a low-dimensional belief field using a transparent SVD layer.

This provides an explicit object for testing the claim that *predictions of other participants' predictions* contain incremental information.

## Why synthetic worlds first

Real markets do not reveal ground-truth mechanisms. A profitable or accurate backtest can still validate the wrong story. The synthetic environment exposes hidden mechanisms to the evaluator while hiding them from the learner.

V1 therefore scores:

- observational similarity of competing worlds
- internal mechanical separation
- identification posterior
- entropy reduction
- active-event selection vs random-event selection
- incremental value of second-order beliefs

Only after these tests are stable should the architecture be frozen and exposed to sealed historical data.
