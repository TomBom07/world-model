from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.tree import DecisionTreeRegressor


@dataclass(frozen=True)
class SplitProposal:
    dimension: int
    threshold: float
    variance_reduction: float


@dataclass(frozen=True)
class MergeProposal:
    left: int
    right: int
    correlation: float


@dataclass(frozen=True)
class OntologyEvolutionResult:
    splits: tuple[SplitProposal, ...]
    merges: tuple[MergeProposal, ...]


class OntologyEvolutionDetector:
    """Suggest when a learned vocabulary should split or merge.

    Split test: if a one-threshold partition of a latent coordinate explains a large
    share of systematic residual variance, that coordinate may be hiding multiple
    regimes/concepts.

    Merge test: if two latent coordinates are almost redundant, maintaining both may
    be unnecessary. These are proposals for a new ontology, not automatic truth.
    """

    def __init__(
        self,
        *,
        split_gain: float = 0.18,
        merge_correlation: float = 0.96,
        min_leaf: int = 16,
    ) -> None:
        self.split_gain = float(split_gain)
        self.merge_correlation = float(merge_correlation)
        self.min_leaf = int(min_leaf)

    def analyze(
        self,
        z: np.ndarray,
        residuals: np.ndarray,
    ) -> OntologyEvolutionResult:
        z = np.asarray(z, dtype=float)
        residuals = np.asarray(residuals, dtype=float).reshape(-1)
        if z.ndim != 2 or len(z) != len(residuals):
            raise ValueError("z and residuals must align")
        if len(z) < self.min_leaf * 3:
            raise ValueError("not enough observations for ontology evolution")

        baseline_sse = float(np.sum((residuals - residuals.mean()) ** 2))
        splits: list[SplitProposal] = []
        for dim in range(z.shape[1]):
            tree = DecisionTreeRegressor(
                max_depth=1,
                min_samples_leaf=self.min_leaf,
                random_state=17 + dim,
            )
            tree.fit(z[:, [dim]], residuals)
            prediction = tree.predict(z[:, [dim]])
            sse = float(np.sum((residuals - prediction) ** 2))
            gain = (baseline_sse - sse) / max(baseline_sse, 1e-12)
            threshold = float(tree.tree_.threshold[0])
            if threshold > -1.5 and gain >= self.split_gain:
                splits.append(
                    SplitProposal(
                        dimension=dim,
                        threshold=threshold,
                        variance_reduction=float(gain),
                    )
                )

        merges: list[MergeProposal] = []
        if z.shape[1] > 1:
            corr = np.corrcoef(z, rowvar=False)
            for left in range(z.shape[1]):
                for right in range(left + 1, z.shape[1]):
                    value = float(corr[left, right])
                    if np.isfinite(value) and abs(value) >= self.merge_correlation:
                        merges.append(
                            MergeProposal(
                                left=left,
                                right=right,
                                correlation=value,
                            )
                        )

        splits.sort(key=lambda item: item.variance_reduction, reverse=True)
        merges.sort(key=lambda item: abs(item.correlation), reverse=True)
        return OntologyEvolutionResult(
            splits=tuple(splits),
            merges=tuple(merges),
        )
