from __future__ import annotations

import numpy as np

from worldmodel.custom_world import analyze_custom_world


def test_custom_world_finds_predictive_structure_on_untouched_holdout() -> None:
    rng = np.random.default_rng(17)
    rows = []
    for i in range(180):
        x0 = rng.normal()
        x1 = rng.normal()
        x2 = rng.normal()
        y = 3.0 + 1.8 * x0 - 0.9 * (x1 ** 2) + 0.05 * rng.normal()
        rows.append([x0, x1, x2, y])

    result = analyze_custom_world(
        columns=["x0", "x1", "x2", "target"],
        rows=rows,
        target="target",
        features=["x0", "x1", "x2"],
        seed=7,
    )

    assert result["dataset"]["train_rows"] + result["dataset"]["holdout_rows"] == 180
    assert result["symbolic_model"]["holdout"]["r2"] > 0.95
    assert result["symbolic_model"]["holdout"]["mae"] < result["baselines"]["mean"]["mae"]
    assert result["symbolic_model"]["terms"]
    assert result["preprocessing"]["standardized_from_training_only"]
    assert result["feature_importance"][0]["feature"] in {"x0", "x1"}


def test_custom_world_drops_incomplete_rows_and_reports_them() -> None:
    rows = [[float(i), float(i * 2)] for i in range(40)]
    rows.append([None, 4.0])
    rows.append([2.0, "not-a-number"])

    result = analyze_custom_world(
        columns=["x", "y"],
        rows=rows,
        target="y",
        features=["x"],
    )

    assert result["dataset"]["rows_received"] == 42
    assert result["dataset"]["rows_used"] == 40
    assert result["dataset"]["rows_dropped"] == 2


def test_custom_world_rejects_too_many_features() -> None:
    columns = [f"x{i}" for i in range(9)] + ["y"]
    rows = [[float(i + j) for j in range(9)] + [float(i)] for i in range(40)]

    try:
        analyze_custom_world(
            columns=columns,
            rows=rows,
            target="y",
            features=columns[:-1],
        )
    except ValueError as error:
        assert "at most 8 features" in str(error)
    else:
        raise AssertionError("Expected too-many-features validation failure")
