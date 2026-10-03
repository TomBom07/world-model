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

    Contiguous windows are summarized and clustered into candidate environments.
    Mean shifts are the default signal because short-window variance estimates are
    noisy enough to create spurious extra regimes. Scale changes can be included
    explicitly when they are scientifically motivated.

    The inferred labels are hypotheses about natural experiments, not causal truth.
    """

    def __init__(
        self,
        *,
        window: int = 24,
        max_regimes: int = 6,
        include_scale: bool = False,
        seed: int = 7,
    ) -> None:
        if window < 4 or max_regimes < 2:
            raise ValueError("window must be >=4 and max_regimes >=2")
        self.window = int(window)
        self.max_regimes = int(max_regimes)
        self.include_scale = bool(include_scale)
        self.seed = int(seed)

    def _summary(self, block: np.ndarray) -> np.ndarray:
        mean = block.mean(axis=0)
        if not self.include_scale:
            return mean
        return np.r_[mean, block.std(axis=0)]

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
                    summaries[-1] = self._summary(x[prev_start:end])
                break
            block = x[start:end]
            chunks.append((start, end))
            summaries.append(self._summary(block))

        summary = StandardScaler().fit_transform(np.vstack(summaries))
        if len(summary) < 4:
            raise ValueError("not enough blocks to discover natural environments")

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
