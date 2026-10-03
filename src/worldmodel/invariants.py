from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .compiler import CompilerResult


@dataclass(frozen=True)
class InvariantPrediction:
    mean: float
    low: float
    high: float
    positive_mass: float
    negative_mass: float
    consensus: float
    robust: bool


def _weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]
    weights = weights / weights.sum()
    cdf = np.cumsum(weights) - 0.5 * weights
    return float(np.interp(q, cdf, values, left=values[0], right=values[-1]))


def prediction_invariant(
    result: CompilerResult,
    x_row: np.ndarray,
    *,
    consensus_threshold: float = 0.85,
) -> InvariantPrediction:
    row = np.asarray(x_row, dtype=float).reshape(1, -1)
    preds, weights = result.ensemble_predictions(row)
    values = preds[:, 0]
    mean = float(np.sum(values * weights))
    positive = float(weights[values > 0].sum())
    negative = float(weights[values < 0].sum())
    consensus = max(positive, negative)
    return InvariantPrediction(
        mean=mean,
        low=_weighted_quantile(values, weights, 0.10),
        high=_weighted_quantile(values, weights, 0.90),
        positive_mass=positive,
        negative_mass=negative,
        consensus=consensus,
        robust=bool(consensus >= consensus_threshold),
    )
