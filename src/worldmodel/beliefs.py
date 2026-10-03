from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .strategic import StrategicWorld


@dataclass(frozen=True)
class BeliefField:
    scores: np.ndarray
    loadings: np.ndarray
    explained_variance_ratio: np.ndarray
    disagreement: np.ndarray
    higher_order_gap: np.ndarray
    labels: tuple[str, ...]

    def summary(self, top_k: int = 4) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for i, ratio in enumerate(self.explained_variance_ratio):
            order = np.argsort(np.abs(self.loadings[:, i]))[::-1]
            rows.append(
                {
                    "factor": i + 1,
                    "explained_variance": float(ratio),
                    "dominant_dimensions": [
                        {
                            "dimension": self.labels[j],
                            "loading": float(self.loadings[j, i]),
                        }
                        for j in order[:top_k]
                    ],
                }
            )
        return rows


def compress_belief_field(world: StrategicWorld, n_factors: int = 4) -> BeliefField:
    """Compress first- and second-order beliefs into a latent belief field."""
    first_mean = world.first_order_beliefs.mean(axis=1)
    second_mean = world.second_order_beliefs.mean(axis=1)
    disagreement = world.first_order_beliefs.std(axis=1)
    gap = second_mean - first_mean

    matrix = np.column_stack([first_mean, second_mean, disagreement, gap])

    labels: list[str] = []
    for prefix in ("first", "second", "disagreement", "higher_order_gap"):
        labels.extend(f"{prefix}:{asset}" for asset in world.asset_names)

    mean = matrix.mean(axis=0, keepdims=True)
    scale = matrix.std(axis=0, keepdims=True)
    scale[scale < 1e-9] = 1.0
    z = (matrix - mean) / scale

    u, s, vt = np.linalg.svd(z, full_matrices=False)
    k = min(max(1, int(n_factors)), len(s))
    variance = s**2
    ratio = variance[:k] / max(float(variance.sum()), 1e-12)
    return BeliefField(
        scores=u[:, :k] * s[:k],
        loadings=vt[:k].T,
        explained_variance_ratio=ratio,
        disagreement=disagreement,
        higher_order_gap=gap,
        labels=tuple(labels),
    )
