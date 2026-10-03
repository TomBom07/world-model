from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .compiler import MechanismCompiler


@dataclass(frozen=True)
class CustomWorldInput:
    columns: tuple[str, ...]
    rows: tuple[tuple[float | None, ...], ...]
    target: str
    features: tuple[str, ...]


def _metric_bundle(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "r2": float(r2_score(y_true, y_pred)) if len(y_true) > 1 else 0.0,
    }


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    normalized = value
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        # Common European CSV format: semicolon-separated columns with decimal commas.
        if "," in normalized and "." not in normalized:
            normalized = normalized.replace(",", ".")
    try:
        number = float(normalized)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _validate_names(columns: Sequence[str], target: str, features: Sequence[str]) -> None:
    if not columns:
        raise ValueError("The dataset has no columns.")
    if len(set(columns)) != len(columns):
        raise ValueError("Column names must be unique.")
    if target not in columns:
        raise ValueError(f"Target column {target!r} was not found.")
    if not features:
        raise ValueError("Select at least one feature.")
    if len(features) > 8:
        raise ValueError("Select at most 8 features for the symbolic search.")
    if len(set(features)) != len(features):
        raise ValueError("Feature names must be unique.")
    missing = [name for name in features if name not in columns]
    if missing:
        raise ValueError(f"Unknown feature columns: {', '.join(missing)}")
    if target in features:
        raise ValueError("The target cannot also be used as a feature.")


def analyze_custom_world(
    *,
    columns: Sequence[str],
    rows: Sequence[Sequence[object]],
    target: str,
    features: Sequence[str],
    holdout_fraction: float = 0.20,
    seed: int = 7,
) -> dict[str, object]:
    columns = tuple(str(name).strip() for name in columns)
    target = str(target).strip()
    features = tuple(str(name).strip() for name in features)
    _validate_names(columns, target, features)

    if not 0.15 <= float(holdout_fraction) <= 0.40:
        raise ValueError("holdout_fraction must be between 0.15 and 0.40.")

    index = {name: i for i, name in enumerate(columns)}
    selected_indices = [index[name] for name in features]
    target_index = index[target]

    clean_x: list[list[float]] = []
    clean_y: list[float] = []
    dropped = 0

    for row in rows:
        if len(row) != len(columns):
            dropped += 1
            continue
        y_value = _as_float(row[target_index])
        feature_values = [_as_float(row[i]) for i in selected_indices]
        if y_value is None or any(value is None for value in feature_values):
            dropped += 1
            continue
        clean_x.append([float(value) for value in feature_values if value is not None])
        clean_y.append(float(y_value))

    x = np.asarray(clean_x, dtype=float)
    y = np.asarray(clean_y, dtype=float)

    if len(y) < 32:
        raise ValueError(
            f"Rook needs at least 32 complete numeric rows after cleaning; found {len(y)}."
        )
    if x.ndim != 2 or x.shape[1] != len(features):
        raise ValueError("Could not construct a numeric feature matrix.")

    test_count = max(8, int(round(len(y) * float(holdout_fraction))))
    train_count = len(y) - test_count
    if train_count < 24:
        raise ValueError("Not enough training rows remain after creating the holdout.")

    x_train_raw = x[:train_count]
    x_test_raw = x[train_count:]
    y_train = y[:train_count]
    y_test = y[train_count:]

    mean = x_train_raw.mean(axis=0)
    scale = x_train_raw.std(axis=0)
    scale = np.where(scale < 1e-9, 1.0, scale)
    x_train = (x_train_raw - mean) / scale
    x_test = (x_test_raw - mean) / scale

    symbolic_names = tuple(f"z({name})" for name in features)
    compiler = MechanismCompiler(
        max_terms=4,
        beam_width=40,
        top_k=12,
        complexity_penalty=0.65,
    )
    result = compiler.fit(x_train, y_train, symbolic_names)
    best = result.best

    train_pred = best.predict(x_train)
    test_pred = best.predict(x_test)
    symbolic_train = _metric_bundle(y_train, train_pred)
    symbolic_holdout = _metric_bundle(y_test, test_pred)

    mean_pred = np.full_like(y_test, y_train.mean(), dtype=float)
    mean_holdout = _metric_bundle(y_test, mean_pred)

    ridge = Ridge(alpha=1.0)
    ridge.fit(x_train, y_train)
    ridge_holdout = _metric_bundle(y_test, ridge.predict(x_test))

    ensemble_pred, weights = result.ensemble_predictions(x_test)
    ensemble_mean = np.sum(ensemble_pred * weights[:, None], axis=0)
    ensemble_spread = np.sqrt(
        np.sum(weights[:, None] * (ensemble_pred - ensemble_mean[None, :]) ** 2, axis=0)
    )

    rng = np.random.default_rng(seed + 91_337)
    base_mae = symbolic_holdout["mae"]
    feature_importance: list[dict[str, float | str]] = []
    for i, name in enumerate(features):
        permuted = x_test.copy()
        permuted[:, i] = rng.permutation(permuted[:, i])
        mae = float(mean_absolute_error(y_test, best.predict(permuted)))
        feature_importance.append(
            {
                "feature": name,
                "mae_increase": float(mae - base_mae),
                "permuted_mae": mae,
            }
        )
    feature_importance.sort(key=lambda item: float(item["mae_increase"]), reverse=True)

    correlations: list[dict[str, float | str]] = []
    for i, name in enumerate(features):
        xi = x_train_raw[:, i]
        if np.std(xi) < 1e-12 or np.std(y_train) < 1e-12:
            corr = 0.0
        else:
            corr = float(np.corrcoef(xi, y_train)[0, 1])
        correlations.append({"feature": name, "correlation": corr})
    correlations.sort(key=lambda item: abs(float(item["correlation"])), reverse=True)

    train_min = x_train_raw.min(axis=0)
    train_max = x_train_raw.max(axis=0)
    outside = np.logical_or(x_test_raw < train_min, x_test_raw > train_max)
    extrapolation_fraction = float(outside.mean())

    top_models = [
        {
            "rank": i + 1,
            "program": model.as_program(),
            "posterior": float(model.posterior),
            "complexity": int(model.complexity),
            "train_mse": float(model.mse),
            "terms": list(model.term_names),
        }
        for i, model in enumerate(result.models[:6])
    ]

    better_than_mean = symbolic_holdout["mae"] < mean_holdout["mae"]
    better_than_ridge = symbolic_holdout["mae"] < ridge_holdout["mae"]
    if better_than_mean and better_than_ridge:
        verdict = "The compact symbolic model generalizes better than both simple baselines on this holdout."
    elif better_than_mean:
        verdict = "The symbolic model beats the mean baseline, but not the ridge baseline on this holdout."
    else:
        verdict = "The symbolic model does not beat the simple mean baseline on this holdout."

    return {
        "dataset": {
            "rows_received": int(len(rows)),
            "rows_used": int(len(y)),
            "rows_dropped": int(dropped),
            "columns": list(columns),
            "target": target,
            "features": list(features),
            "train_rows": int(train_count),
            "holdout_rows": int(test_count),
            "holdout_strategy": "last rows in uploaded order",
        },
        "preprocessing": {
            "standardized_from_training_only": True,
            "feature_means": {name: float(value) for name, value in zip(features, mean, strict=True)},
            "feature_scales": {name: float(value) for name, value in zip(features, scale, strict=True)},
        },
        "symbolic_model": {
            "program": best.as_program(),
            "terms": list(best.term_names),
            "posterior": float(best.posterior),
            "complexity": int(best.complexity),
            "train": symbolic_train,
            "holdout": symbolic_holdout,
            "ensemble_mean_spread": float(np.mean(ensemble_spread)),
            "top_models": top_models,
        },
        "baselines": {
            "mean": mean_holdout,
            "ridge": ridge_holdout,
        },
        "feature_importance": feature_importance,
        "training_correlations": correlations,
        "extrapolation_fraction": extrapolation_fraction,
        "verdict": verdict,
        "scientific_boundary": (
            "This analysis discovers compact predictive associations in the uploaded numeric table. "
            "The holdout was not used during symbolic search, but a single uploaded dataset does not "
            "establish causality, invariance under intervention, or prospective real-world validity."
        ),
    }
