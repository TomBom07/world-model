import numpy as np

from worldmodel.beliefs import compress_belief_field
from worldmodel.evaluation import (
    active_identification_benchmark,
    belief_order_ablation,
    observational_equivalence,
)
from worldmodel.identification import ActiveWorldIdentifier
from worldmodel.strategic import StrategicMarketSimulator


def test_two_hidden_worlds_are_observationally_similar_but_mechanically_different():
    simulator = StrategicMarketSimulator(seed=7)
    belief_world, liquidity_world = simulator.paired_worlds(n=220)
    metrics = observational_equivalence(belief_world, liquidity_world, prefix=100)

    assert metrics.mean_return_correlation > 0.99
    assert metrics.mean_normalized_mae < 0.10
    assert liquidity_world.leverage[:, 4].mean() > belief_world.leverage[:, 4].mean()
    assert np.abs(liquidity_world.dealer_hedge).mean() > 1.5 * np.abs(belief_world.dealer_hedge).mean()


def test_active_identifier_chooses_diagnostic_probe_and_updates_true_world():
    simulator = StrategicMarketSimulator(seed=7)
    events = simulator.generate_events(220)
    identifier = ActiveWorldIdentifier(simulator, observation_sigma=0.08)
    ranked = identifier.rank_probes(events, event_index=140)

    assert ranked[0].probe.event_kind == "liquidity"
    result = identifier.observe_ranked(
        ranked[0],
        true_mechanism="liquidity_reflexive",
        observation_seed=30_008,
    )
    assert result.predicted_mechanism == "liquidity_reflexive"
    assert result.posterior["liquidity_reflexive"] > 0.70
    assert result.entropy_after < result.entropy_before


def test_higher_order_beliefs_are_explicit_and_testable():
    world = StrategicMarketSimulator(seed=9).simulate("belief_reflexive", n=220)
    field = compress_belief_field(world, n_factors=3)
    ablation = belief_order_ablation(world)

    assert field.scores.shape == (220, 3)
    assert field.higher_order_gap.shape == (220, len(world.asset_names))
    assert np.isfinite(ablation.first_order_mae)
    assert np.isfinite(ablation.first_plus_second_order_mae)


def test_active_identification_beats_random_probe_on_information_gain():
    benchmark = active_identification_benchmark(trials=6, n=220, event_index=145)
    assert benchmark.active_true_posterior > benchmark.random_true_posterior
    assert benchmark.active_entropy_reduction > benchmark.random_entropy_reduction
