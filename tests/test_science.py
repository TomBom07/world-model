import numpy as np

from worldmodel.adversary import stress_test
from worldmodel.compiler import MechanismCompiler
from worldmodel.invariants import prediction_invariant
from worldmodel.ontology import suggest_missing_mechanisms
from worldmodel.regimes import ResidualRegimeDetector
from worldmodel.simulator import ReflexiveMarketSimulator
from worldmodel.tomography import belief_tomography


def test_tomography_shapes():
    world = ReflexiveMarketSimulator(seed=1).generate(n=140)
    result = belief_tomography(world.y, world.target_names, n_factors=3)
    assert result.scores.shape == (140, 3)
    assert result.loadings.shape == (6, 3)
    assert 0 < result.explained_variance_ratio.sum() <= 1


def test_regime_detector_finds_error_shift():
    rng = np.random.default_rng(2)
    residuals = np.r_[rng.normal(0, 0.08, 90), rng.normal(0, 1.0, 90)]
    result = ResidualRegimeDetector(window=18, threshold=2.0).detect(residuals)
    assert result.detected
    assert result.index is not None
    assert abs(result.index - 90) <= 15


def test_ontology_finds_missing_interaction():
    rng = np.random.default_rng(3)
    x = rng.normal(size=(260, 3))
    residuals = 1.7 * x[:, 0] * x[:, 2] + rng.normal(0, 0.1, 260)
    suggestions = suggest_missing_mechanisms(x, residuals, ["a", "b", "c"], top_k=3)
    assert suggestions[0].expression == "a*c"
    assert suggestions[0].strength > 0.9


def test_invariant_and_adversary_run():
    rng = np.random.default_rng(5)
    x = rng.normal(size=(200, 2))
    y = 1.4 * x[:, 0] - 0.5 * x[:, 1] + rng.normal(0, 0.08, 200)
    result = MechanismCompiler(max_terms=2, top_k=8).fit(x, y, ["a", "b"])
    inv = prediction_invariant(result, np.array([1.2, 0.1]))
    assert inv.mean > 0
    assert 0 <= inv.consensus <= 1
    scenarios = stress_test(result, np.array([1.2, 0.1]), ["a", "b"], magnitude=2.0)
    assert scenarios
