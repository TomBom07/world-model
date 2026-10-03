# WorldModel — Reflexive Mechanism Compiler

> Infer the smallest executable mechanism that explains how a changing world updates itself — then actively seek the observation that can disprove it.

WorldModel is a research lab, not a stock-prediction bot. The project asks whether a machine can recover hidden mechanisms in a reflexive world, notice when its explanation breaks, model beliefs about beliefs, and choose the next observation that is most informative.

## V1: strategic hidden worlds

V1 makes the problem deliberately harder.

Two synthetic markets can produce **nearly indistinguishable ordinary price histories** while being driven by different hidden mechanisms:

- **belief-reflexive world** — participants react strongly to what they believe other participants believe and will do;
- **liquidity-reflexive world** — liquidity, leverage constraints, forced deleveraging and dealer hedging dominate.

Both worlds contain six populations:

```text
fundamental funds
macro funds
momentum
retail
leveraged funds
dealers
```

Each population has private first-order beliefs, estimates of the market's beliefs, a reaction rule and constraints.

WorldModel then asks:

> Which naturally occurring future event would cause these candidate worlds to react most differently?

It pre-registers each world's cross-asset reaction fingerprint, waits for that diagnostic event in the synthetic environment, observes the reaction and updates the probability of each hidden mechanism.

That is **active world identification**, not simply forecasting the next price.

## V2: sealed historical replay

V2 adds the infrastructure required before touching real historical outcomes:

- timestamped event datasets with per-feature availability times
- hard look-ahead leakage rejection
- immutable experiment specifications
- SHA-256 manifest, dataset and forecast seals
- frozen train/evaluation boundaries
- event-level reaction fingerprints
- calibrated 80% prediction intervals
- RMC compared under the same protocol against Ridge, Random Forest, MLP and a local-level state-space baseline
- MAE, RMSE, directional accuracy, Gaussian log score and interval coverage
- CSV schema for future real event datasets

The included V2 demo still uses **historical-shaped synthetic events**. That is deliberate: the evaluation machinery is being tested before we expose it to real outcomes and create researcher degrees of freedom.

## Implemented


### V0 — mechanism compilation

- compact symbolic mechanism search
- MDL-style complexity selection
- population of plausible executable models
- residual regime-break detection
- ontology-break suggestions
- belief tomography
- prediction invariants
- adversarial counterfactual testing
- sample-efficiency baselines

### V1 — reflexive strategic worlds

- six heterogeneous market populations
- private information and noisy beliefs
- explicit second-order beliefs: beliefs about market consensus
- dynamic leverage
- margin / forced-deleveraging events
- dealer gamma hedging
- two observationally similar worlds with different hidden causes
- cross-asset counterfactual reaction fingerprints
- active diagnostic-event selection
- Bayes-style hidden-mechanism updating
- higher-order-belief compression
- first-order vs first+second-order ablation
- active-vs-random identification benchmark
- interactive dashboard for inspecting the full experiment

## Architecture

```text
                    observations
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
 symbolic mechanism compiler     strategic world models
          │                             │
          ▼                             ▼
 competing executable models      belief / liquidity hypotheses
          │                             │
          ├── regime break              ├── first-order beliefs
          ├── ontology break            ├── second-order beliefs
          ├── invariants                ├── leverage / margin
          └── destroyer                 └── dealer hedging
                                          │
                                          ▼
                                  reaction fingerprints
                                          │
                                          ▼
                                  ACTIVE IDENTIFIER
                                          │
                             "what should we observe next?"
                                          │
                                          ▼
                                   posterior update
```

The long-term target is not merely:

```text
world_t → world_t+1
```

but:

```text
(M_t, world_t) → (M_t+1, world_t+1)
```

where the system also learns how the world's update rule itself changes.

## Run it

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"

pytest
worldmodel demo
worldmodel strategic
worldmodel sealed
worldmodel serve --reload
```

Open `http://127.0.0.1:8000`.

## Research discipline

V0 and V1 use **synthetic worlds whose hidden mechanisms are known to the evaluator**. This is intentional. A historical market backtest can reward a wrong explanation; synthetic worlds let us directly score whether the model recovered the actual generating mechanism.

The project does **not** claim real-market alpha. No output is investment advice or a trading signal.

The sealed historical protocol is now implemented. The next step is to freeze a real event schema and ingest real earnings / CPI / central-bank / liquidity event windows without changing the evaluation rules after seeing the holdout results.

See [`docs/research-plan.md`](docs/research-plan.md) and [`docs/architecture.md`](docs/architecture.md).
