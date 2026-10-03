import numpy as np

from worldmodel.physics import HiddenPhysicsSimulator
from worldmodel.physics_engine import PhysicsDiscoveryEngine


def test_passive_physics_worlds_are_locally_indistinguishable():
    simulator = HiddenPhysicsSimulator(seed=7)
    metrics = simulator.passive_equivalence(n=240, prefix=120)

    assert metrics["velocity_correlation"] > 0.999
    assert metrics["velocity_normalized_mae"] < 0.01

    v = simulator.reference_velocity
    eps = 1e-5
    linear_value = simulator.resistance("linear_resistance", v)
    curved_value = simulator.resistance("curved_resistance", v)
    linear_slope = (
        simulator.resistance("linear_resistance", v + eps)
        - simulator.resistance("linear_resistance", v - eps)
    ) / (2 * eps)
    curved_slope = (
        simulator.resistance("curved_resistance", v + eps)
        - simulator.resistance("curved_resistance", v - eps)
    ) / (2 * eps)

    assert np.isclose(linear_value, curved_value, atol=1e-10)
    assert np.isclose(linear_slope, curved_slope, rtol=1e-5)


def test_active_physics_probe_identifies_hidden_law():
    result = PhysicsDiscoveryEngine(seed=7).run_demo(n=240)
    active = result["active_identification"]
    truth = result["experiment"]["true_mechanism"]

    assert active["correct"]
    assert active["posterior"][truth] > 0.90
    assert active["entropy_after"] < active["entropy_before"]
    assert active["ranked_probes"][0]["name"] == active["selected_probe"]["name"]


def test_active_physics_experiments_beat_random_choice():
    result = PhysicsDiscoveryEngine(seed=9).benchmark(trials=10, n=220)

    assert result["active_true_posterior"] > result["random_true_posterior"]
    assert result["active_entropy_reduction"] > result["random_entropy_reduction"]
