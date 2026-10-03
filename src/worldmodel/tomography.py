from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TomographyResult:
    scores: np.ndarray
    loadings: np.ndarray
    explained_variance_ratio: np.ndarray
    labels: tuple[str, ...]

    def summary(self) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for i, ratio in enumerate(self.explained_variance_ratio):
            order = np.argsort(np.abs(self.loadings[:, i]))[::-1]
            result.append(
                {
                    "factor": i + 1,
                    "explained_variance": float(ratio),
                    "dominant_loadings": [
                        {"asset": self.labels[j], "loading": float(self.loadings[j, i])}
                        for j in order[:3]
                    ],
                }
            )
        return result


def belief_tomography(
    reaction_matrix: np.ndarray,
    labels: list[str] | tuple[str, ...],
    n_factors: int = 3,
) -> TomographyResult:
    """Reconstruct low-dimensional reaction factors from cross-asset fingerprints."""
    y = np.asarray(reaction_matrix, dtype=float)
    if y.ndim != 2:
        raise ValueError("reaction_matrix must be 2D")
    if y.shape[1] != len(labels):
        raise ValueError("labels must match reaction columns")

    mean = y.mean(axis=0, keepdims=True)
    scale = y.std(axis=0, keepdims=True)
    scale[scale < 1e-9] = 1.0
    z = (y - mean) / scale
    u, s, vt = np.linalg.svd(z, full_matrices=False)
    k = min(n_factors, len(s))
    variance = s**2
    ratio = variance[:k] / max(variance.sum(), 1e-12)
    scores = u[:, :k] * s[:k]
    loadings = vt[:k].T
    return TomographyResult(
        scores=scores,
        loadings=loadings,
        explained_variance_ratio=ratio,
        labels=tuple(labels),
    )
