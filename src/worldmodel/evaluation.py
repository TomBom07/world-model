from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error

from .identification import ActiveWorldIdentifier
from .strategic import MECHANISMS, StrategicMarketSimulator, StrategicWorld


@dataclass(frozen=True)
class EquivalenceMetrics:
    prefix: int
    mean_return_correlation: float
    mean_normalized_mae: float
    max_asset_normalized_mae: float


@dataclass(frozen=True)
class BeliefAblation:
    mechanism: str
    first_order_mae: float
    first_plus_second_order_mae: float
    relative_improvement: float


@dataclass(frozen=True)
class IdentificationBenchmark:
    trials: int
    active_accuracy: float
    random_accuracy: float
    active_true_posterior: float
    random_true_posterior: float
    active_entropy_reduction: float
    random_entropy_reduction: float


def observational_equivalence(
    a: StrategicWorld,
    b: StrategicWorld,
    *,
    prefix: int = 120,
) -> EquivalenceMetrics:
    prefix = min(prefix, len(a.returns), len(b.returns))
    if prefix < 8:
        raise ValueError("prefix must include at least 8 observations")

    correlations: list[float] = []
    normalized_errors: list[float] = []
    for column in range(a.returns.shape[1]):
        left = a.returns[:prefix, column]
        right = b.returns[:prefix, column]
        correlations.append(float(np.corrcoef(left, right)[0, 1]))
        scale = max(1e-9, 0.5 * (left.std() + right.std()))
        normalized_errors.append(float(np.mean(np.abs(left - right)) / scale))

    return EquivalenceMetrics(
        prefix=prefix,
        mean_return_correlation=float(np.mean(correlations)),
        mean_normalized_mae=float(np.mean(normalized_errors)),
        max_asset_normalized_mae=float(np.max(normalized_errors)),
    )


def belief_order_ablation(world: StrategicWorld, *, train_fraction: float = 0.70) -> BeliefAblation:
    """Measure whether explicit second-order beliefs add predictive information."""
    split = int(len(world.returns) * train_fraction)
    split = min(max(split, 24), len(world.returns) - 16)

    first = world.first_order_beliefs.mean(axis=1)
    second = world.second_order_beliefs.mean(axis=1)
    combined = np.column_stack([first, second])

    first_model = Ridge(alpha=1.0).fit(first[:split], world.returns[:split])
    combined_model = Ridge(alpha=1.0).fit(combined[:split], world.returns[:split])

    first_mae = float(
        mean_absolute_error(world.returns[split:], first_model.predict(first[split:]))
    )
    combined_mae = float(
        mean_absolute_error(
            world.returns[split:],
            combined_model.predict(combined[split:]),
        )
    )
    improvement = float((first_mae - combined_mae) / max(first_mae, 1e-12))

    return BeliefAblation(
        mechanism=world.mechanism,
        first_order_mae=first_mae,
        first_plus_second_order_mae=combined_mae,
        relative_improvement=improvement,
    )


def active_identification_benchmark(
    *,
    trials: int = 12,
    n: int = 220,
    event_index: int = 145,
    observation_sigma: float = 0.08,
) -> IdentificationBenchmark:
    """Compare information-seeking event selection with a random future event."""
    active_correct: list[float] = []
    random_correct: list[float] = []
    active_true_mass: list[float] = []
    random_true_mass: list[float] = []
    active_entropy_gain: list[float] = []
    random_entropy_gain: list[float] = []

    for seed in range(trials):
        simulator = StrategicMarketSimulator(seed=seed)
        events = simulator.generate_events(n)
        identifier = ActiveWorldIdentifier(
            simulator,
            observation_sigma=observation_sigma,
        )
        ranked = identifier.rank_probes(events, event_index)
        active_probe = ranked[0]

        chooser = np.random.default_rng(seed + 81_337)
        random_probe = ranked[int(chooser.integers(0, len(ranked)))]
        true_mechanism = MECHANISMS[seed % len(MECHANISMS)]

        active = identifier.observe_ranked(
            active_probe,
            true_mechanism=true_mechanism,
            observation_seed=seed + 30_001,
        )
        random_result = identifier.observe_ranked(
            random_probe,
            true_mechanism=true_mechanism,
            observation_seed=seed + 40_001,
        )

        active_correct.append(float(bool(active.correct)))
        random_correct.append(float(bool(random_result.correct)))
        active_true_mass.append(active.posterior[true_mechanism])
        random_true_mass.append(random_result.posterior[true_mechanism])
        active_entropy_gain.append(active.entropy_before - active.entropy_after)
        random_entropy_gain.append(random_result.entropy_before - random_result.entropy_after)

    return IdentificationBenchmark(
        trials=trials,
        active_accuracy=float(np.mean(active_correct)),
        random_accuracy=float(np.mean(random_correct)),
        active_true_posterior=float(np.mean(active_true_mass)),
        random_true_posterior=float(np.mean(random_true_mass)),
        active_entropy_reduction=float(np.mean(active_entropy_gain)),
        random_entropy_reduction=float(np.mean(random_entropy_gain)),
    )


def strategic_diagnostics(seed: int = 7, n: int = 260) -> dict[str, object]:
    simulator = StrategicMarketSimulator(seed=seed)
    belief_world, liquidity_world = simulator.paired_worlds(n=n)
    return {
        "observational_equivalence": asdict(
            observational_equivalence(belief_world, liquidity_world, prefix=min(120, n // 2))
        ),
        "belief_ablation": [
            asdict(belief_order_ablation(belief_world)),
            asdict(belief_order_ablation(liquidity_world)),
        ],
        "hidden_mechanics": {
            "belief_reflexive": {
                "mean_leverage": float(belief_world.leverage[:, 4].mean()),
                "dealer_hedge_magnitude": float(np.mean(np.abs(belief_world.dealer_hedge))),
                "margin_calls": belief_world.margin_call_count,
            },
            "liquidity_reflexive": {
                "mean_leverage": float(liquidity_world.leverage[:, 4].mean()),
                "dealer_hedge_magnitude": float(np.mean(np.abs(liquidity_world.dealer_hedge))),
                "margin_calls": liquidity_world.margin_call_count,
            },
        },
    }
