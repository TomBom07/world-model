import numpy as np

from worldmodel.compiler import MechanismCompiler
from worldmodel.mechanisms import build_terms


def test_term_library_contains_interactions():
    names = [t.name for t in build_terms(["a", "b", "c"])]
    assert "a*b" in names
    assert "c^2" in names


def test_compiler_recovers_sparse_interaction():
    rng = np.random.default_rng(4)
    x = rng.normal(size=(220, 3))
    y = 0.7 * x[:, 0] - 1.3 * x[:, 1] * x[:, 2] + rng.normal(0, 0.04, size=len(x))
    result = MechanismCompiler(max_terms=3, beam_width=28, top_k=10).fit(x, y, ["a", "b", "c"])
    assert "a" in result.best.term_names
    assert "b*c" in result.best.term_names
    assert result.best.mse < 0.01


def test_posterior_weights_are_normalized():
    rng = np.random.default_rng(8)
    x = rng.normal(size=(100, 2))
    y = x[:, 0] + rng.normal(0, 0.1, size=100)
    result = MechanismCompiler(max_terms=2).fit(x, y, ["x", "z"])
    assert np.isclose(sum(m.posterior for m in result.models), 1.0)
