from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np


@dataclass(frozen=True)
class OntologySuggestion:
    expression: str
    residual_correlation: float
    strength: float


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.std() < 1e-10 or b.std() < 1e-10:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def suggest_missing_mechanisms(
    x: np.ndarray,
    residuals: np.ndarray,
    feature_names: list[str] | tuple[str, ...],
    used_terms: set[str] | frozenset[str] | tuple[str, ...] = (),
    top_k: int = 6,
) -> list[OntologySuggestion]:
    """Look for simple omitted transforms that explain structured residuals."""
    x = np.asarray(x, dtype=float)
    residuals = np.asarray(residuals, dtype=float).reshape(-1)
    used = set(used_terms)
    candidates: list[tuple[str, np.ndarray]] = []

    for i, name in enumerate(feature_names):
        candidates.append((f"{name}^2", x[:, i] ** 2))
    for i, j in combinations(range(len(feature_names)), 2):
        candidates.append((f"{feature_names[i]}*{feature_names[j]}", x[:, i] * x[:, j]))

    suggestions: list[OntologySuggestion] = []
    for name, values in candidates:
        if name in used:
            continue
        c = _corr(residuals, values)
        suggestions.append(
            OntologySuggestion(expression=name, residual_correlation=c, strength=abs(c))
        )
    suggestions.sort(key=lambda item: item.strength, reverse=True)
    return suggestions[:top_k]
