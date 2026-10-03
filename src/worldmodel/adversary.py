from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .compiler import CompilerResult
from .invariants import prediction_invariant


@dataclass(frozen=True)
class AdversarialScenario:
    feature: str
    delta: float
    prediction: float
    consensus: float
    sign_flipped: bool


def stress_test(
    result: CompilerResult,
    x_row: np.ndarray,
    feature_names: list[str] | tuple[str, ...],
    *,
    feature_scales: np.ndarray | None = None,
    magnitude: float = 1.0,
    top_k: int = 6,
) -> list[AdversarialScenario]:
    base = np.asarray(x_row, dtype=float).reshape(-1)
    scales = np.ones_like(base) if feature_scales is None else np.asarray(feature_scales, dtype=float)
    baseline = prediction_invariant(result, base)
    baseline_sign = np.sign(baseline.mean)
    scenarios: list[AdversarialScenario] = []

    for idx, name in enumerate(feature_names):
        for direction in (-1.0, 1.0):
            perturbed = base.copy()
            delta = float(direction * magnitude * max(scales[idx], 1e-6))
            perturbed[idx] += delta
            inv = prediction_invariant(result, perturbed)
            sign_flipped = bool(baseline_sign != 0 and np.sign(inv.mean) != baseline_sign)
            scenarios.append(
                AdversarialScenario(
                    feature=name,
                    delta=delta,
                    prediction=inv.mean,
                    consensus=inv.consensus,
                    sign_flipped=sign_flipped,
                )
            )

    scenarios.sort(key=lambda item: (not item.sign_flipped, item.consensus, abs(item.prediction)))
    return scenarios[:top_k]
