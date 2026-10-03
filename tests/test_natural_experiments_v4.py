import numpy as np

from worldmodel.frontier_bench import _natural_regime_problem
from worldmodel.natural_experiments import NaturalEnvironmentDiscoverer
from sklearn.metrics import adjusted_rand_score


def test_temporal_natural_experiment_discovery_is_stable_across_seeds():
    for seed in (3, 7, 19):
        x, truth = _natural_regime_problem(seed=seed + 77)
        result = NaturalEnvironmentDiscoverer(
            window=24,
            max_regimes=6,
            seed=seed + 77,
        ).fit_transform(x)
        assert result.cluster_count == 4
        assert adjusted_rand_score(truth, result.labels) > 0.95
