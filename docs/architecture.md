# RMC architecture

WorldModel V0 treats forecasting as mechanism inference, not direct next-step price prediction.

## Loop

1. Observe an event/reaction vector.
2. Compile mechanisms from a deliberately small symbolic language.
3. Maintain alternatives using description-length scores converted to posterior-like weights.
4. Detect structural failure when residuals shift.
5. Search the ontology for omitted interactions that explain structured errors.
6. Reconstruct reaction factors with belief tomography.
7. Search for invariants that survive disagreement across plausible programs.
8. Attack the conclusion with counterfactual perturbations.

## Why synthetic worlds first

A real market does not reveal the true causal mechanism, so a good backtest can still reward a wrong story. The synthetic environment exposes the hidden rule to the evaluator while hiding it from the learner. This lets us measure mechanism recovery, change-point localization, sample efficiency and robustness directly.

## Intentionally missing in V0

- live prices or brokerage connectivity
- LLM-generated hypotheses
- event/news ingestion
- higher-order strategic-agent recursion
- Bayesian online program birth/death
- causal interventions on real data

Those are later phases only after the core mechanism-recovery hypothesis survives controlled tests.
