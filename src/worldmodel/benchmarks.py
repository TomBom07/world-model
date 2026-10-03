from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_absolute_error

from .compiler import MechanismCompiler
from .simulator import ReflexiveMarketSimulator


def sample_efficiency_benchmark(
    *,
    seed: int = 17,
    train_sizes: tuple[int, ...] = (24, 40, 64, 96, 144),
) -> list[dict[str, float | int]]:
    """Compare compact mechanism search with two conventional baselines.

    This is a synthetic structured benchmark, not evidence of real-market alpha.
    """
    sim = ReflexiveMarketSimulator(seed=seed, noise=0.16)
    world = sim.generate(n=520, switch_at=1.0)
    target = world.target("growth_equity")
    test_x = world.x[320:]
    test_y = target[320:]
    rows: list[dict[str, float | int]] = []

    for n_train in train_sizes:
        x = world.x[:n_train]
        y = target[:n_train]

        rmc = MechanismCompiler(max_terms=5, beam_width=36, top_k=10).fit(x, y, world.feature_names)
        rmc_pred = rmc.best.predict(test_x)

        ridge = Ridge(alpha=1.0).fit(x, y)
        polynomial_ridge = make_pipeline(
            PolynomialFeatures(degree=2, include_bias=False),
            Ridge(alpha=1.0),
        ).fit(x, y)
        rf = RandomForestRegressor(
            n_estimators=160,
            max_depth=5,
            min_samples_leaf=3,
            random_state=seed,
            n_jobs=1,
        ).fit(x, y)

        rows.append(
            {
                "train_size": n_train,
                "rmc_mae": float(mean_absolute_error(test_y, rmc_pred)),
                "ridge_mae": float(mean_absolute_error(test_y, ridge.predict(test_x))),
                "poly_ridge_mae": float(mean_absolute_error(test_y, polynomial_ridge.predict(test_x))),
                "random_forest_mae": float(mean_absolute_error(test_y, rf.predict(test_x))),
            }
        )
    return rows
