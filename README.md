# WorldModel — Reflexive Mechanism Compiler

> **Research prototype:** infer the smallest executable mechanism that explains how a changing world updates itself.

WorldModel is not a stock-prediction bot. V0 asks a more basic and falsifiable question:

**Can we recover a hidden, changing causal-ish mechanism from sparse observations, detect when that mechanism stops working, and identify conclusions that survive uncertainty across multiple plausible models?**

The first environment is a synthetic reflexive market because its hidden rules are known to the evaluator. That lets us test mechanism recovery without fooling ourselves with a pretty historical backtest.

## What V0 implements

- **Mechanism compiler** — beam-searches a compact symbolic language of primitives, interactions and nonlinear terms, fitting executable programs instead of one opaque model.
- **Description-length selection** — balances predictive fit against program complexity.
- **Model population** — retains multiple plausible mechanisms with posterior-like weights instead of pretending one explanation is certainly true.
- **Regime-break detector** — notices when an old world model begins producing structurally larger errors.
- **Ontology-break search** — inspects residual structure for omitted interactions that may represent a missing concept.
- **Belief tomography** — compresses cross-asset reaction fingerprints into latent factors.
- **Prediction invariants** — reports conclusions shared by most plausible mechanisms.
- **Adversarial destroyer** — perturbs the inferred world and searches for conditions that flip the conclusion.
- **Sample-efficiency benchmark** — compares RMC against linear Ridge, degree-2 polynomial Ridge and Random Forest inside a controlled structured world.
- **Research dashboard** — an interactive local interface for rerunning worlds and inspecting what the compiler recovered.

## Architecture

```text
observations / events
        │
        ▼
reaction fingerprint ──► belief tomography
        │
        ▼
mechanism compiler ──► population of executable programs
        │                         │
        │                         ├──► prediction invariants
        │                         └──► adversarial destroyer
        ▼
residual stream
        │
        ├──► regime-break detector
        └──► ontology-break suggestions
                    │
                    ▼
              revised mechanism
```

The long-term target is a system that learns not only `world_t → world_t+1`, but also how the **update rule itself changes**:

```text
(M_t, world_t) → (M_t+1, world_t+1)
```

## Run it

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
pytest
worldmodel demo
worldmodel serve --reload
```

Open `http://127.0.0.1:8000` for the lab UI.

## Current scientific boundary

V0 uses **synthetic data only**. It tests whether the architecture can recover known mechanisms under regime change. It is **not evidence of real-market alpha**, and no output should be treated as investment advice or a trading signal.

See [`docs/research-plan.md`](docs/research-plan.md) before adding real financial data. The next serious milestone is not “connect Yahoo Finance”; it is making the synthetic worlds harder enough that multiple hidden causes can explain the same superficial price behavior.
