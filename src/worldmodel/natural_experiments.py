from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class NaturalExperimentResult:
    labels: np.ndarray
    descriptors: np.ndarray
    cluster_count: int
    silhouette: float
    block_labels: np.ndarray


class NaturalEnvironmentDiscoverer:
    """Infer intervention-like environments from distributional shifts.

    The time series is summarized in contiguous blocks. Candidate environment counts
    are compared with silhouette score, and the best clustering is expanded back to
    per-observation labels. This is intentionally a discovery heuristic: inferred
    environments are hypotheses about natural experiments, not guaranteed causes.
    """

    def __init__(
        self,
        *,
        window: int = 24,
        max_regimes: int = 6,
        seed: int = 7,
    ) -> None:
        if window < 4 or max_regimes < 2:
            raise ValueError("window must be >=4 and max_regimes >=2")
        self.window = int(window)
        self.max_regimes = int(max_regimes)
        self.seed = int(seed)

    def fit_transform(self, x: np.ndarray) -> NaturalExperimentResult:
        x = np.asarray(x, dtype=float)
        if x.ndim != 2 or len(x) < self.window * 4:
            raise ValueError("x must contain at least four windows")

        chunks: list[tuple[int, int]] = []
        summaries: list[np.ndarray] = []
        for start in range(0, len(x), self.window):
            end = min(len(x), start + self.window)
            if end - start < max(4, self.window // 3):
                if chunks:
                    prev_start, _ = chunks[-1]
                    chunks[-1] = (prev_start, end)
                    block = x[prev_start:end]
                    summaries[-1] = np.r_[block.mean(axis=0), block.std(axis=0)]
                break
            block = x[start:end]
            chunks.append((start, end))
            summaries.append(np.r_[block.mean(axis=0), block.std(axis=0)])

        raw_summary = np.vstack(summaries)
        summary = StandardScaler().fit_transform(raw_summary)
        if len(summary) < 4:
            raise ValueError("not enough blocks to discover natural environments")

        # Natural experiments in ordered data are often regime changes, not an
        # exchangeable bag of clusters. Detect unusually large adjacent shifts first.
        # This keeps temporal contiguity and avoids silhouette's tendency to over-split
        # a stable regime into several visually compact KMeans clusters.
        mean_dim = x.shape[1]
        standardized_means = StandardScaler().fit_transform(raw_summary[:, :mean_dim])
        adjacent_distance = np.linalg.norm(np.diff(standardized_means, axis=0), axis=1)
        median = float(np.median(adjacent_distance))
        mad = float(np.median(np.abs(adjacent_distance - median)))
        robust_scale = max(1e-9, 1.4826 * mad)
        threshold = median + 3.0 * robust_scale
        boundaries = np.flatnonzero(adjacent_distance > threshold) + 1

        segment_count = len(boundaries) + 1
        if 2 <= segment_count <= self.max_regimes:
            block_labels = np.zeros(len(summary), dtype=int)
            for boundary in boundaries:
                block_labels[boundary:] += 1

            labels = np.empty(len(x), dtype=int)
            for label, (start, end) in zip(block_labels, chunks):
                labels[start:end] = int(label)

            if len(np.unique(block_labels)) > 1:
                temporal_silhouette = float(silhouette_score(summary, block_labels))
                unique = np.unique(labels)
                mapping = {value: index for index, value in enumerate(unique)}
                descriptors = np.zeros((len(x), len(unique)), dtype=float)
                for row, label in enumerate(labels):
                    descriptors[row, mapping[int(label)]] = 1.0
                return NaturalExperimentResult(
                    labels=labels,
                    descriptors=descriptors,
                    cluster_count=len(unique),
                    silhouette=temporal_silhouette,
                    block_labels=block_labels,
                )

        best_model: KMeans | None = None
        best_score = -np.inf
        max_k = min(self.max_regimes, len(summary) - 1)
        for k in range(2, max_k + 1):
            model = KMeans(n_clusters=k, n_init=20, random_state=self.seed)
            labels = model.fit_predict(summary)
            if len(np.unique(labels)) < 2:
                continue
            score = float(silhouette_score(summary, labels))
            if score > best_score:
                best_score = score
                best_model = model

        if best_model is None:
            raise RuntimeError("failed to discover candidate environments")

        block_labels = best_model.labels_.astype(int)
        labels = np.empty(len(x), dtype=int)
        for label, (start, end) in zip(block_labels, chunks):
            labels[start:end] = int(label)

        unique = np.unique(labels)
        mapping = {value: index for index, value in enumerate(unique)}
        descriptors = np.zeros((len(x), len(unique)), dtype=float)
        for row, label in enumerate(labels):
            descriptors[row, mapping[int(label)]] = 1.0

        return NaturalExperimentResult(
            labels=labels,
            descriptors=descriptors,
            cluster_count=len(unique),
            silhouette=float(best_score),
            block_labels=block_labels,
        )
