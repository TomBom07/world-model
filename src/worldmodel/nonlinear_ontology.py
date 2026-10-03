from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _safe_scale(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale = np.where(scale < 1e-8, 1.0, scale)
    return mean, scale


def _inverse_sqrt(matrix: np.ndarray, ridge: float) -> np.ndarray:
    matrix = 0.5 * (matrix + matrix.T)
    values, vectors = np.linalg.eigh(matrix)
    values = np.clip(values, ridge, None)
    return (vectors * (1.0 / np.sqrt(values))) @ vectors.T


@dataclass(frozen=True)
class NonlinearOntologyResult:
    input_mean: np.ndarray
    input_scale: np.ndarray
    random_weights: np.ndarray
    random_bias: np.ndarray
    feature_mean: np.ndarray
    feature_scale: np.ndarray
    components: np.ndarray
    canonical_correlations: np.ndarray
    null_thresholds: np.ndarray
    selected_dim: int
    bandwidth: float

    @property
    def max_dim(self) -> int:
        return int(self.components.shape[1])

    def _features(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        xs = (x - self.input_mean) / self.input_scale
        count = self.random_weights.shape[1]
        fourier = np.sqrt(2.0 / max(count, 1)) * np.cos(
            xs @ self.random_weights + self.random_bias
        )
        phi = np.column_stack([xs, fourier])
        return (phi - self.feature_mean) / self.feature_scale

    def transform(self, x: np.ndarray, n_components: int | None = None) -> np.ndarray:
        k = self.selected_dim if n_components is None else int(n_components)
        if not 1 <= k <= self.max_dim:
            raise ValueError(f"n_components must be in [1, {self.max_dim}]")
        return self._features(x) @ self.components[:, :k]


class InterventionAwareOntologyLearner:
    """Nonlinear causal representation learning from known intervention descriptors.

    The observation is first lifted into a random Fourier feature space. Canonical
    directions are then found between that nonlinear observation representation and
    intervention descriptors. This asks for coordinates that preserve how controlled
    changes to the world move the observations, rather than coordinates that merely
    explain raw variance.

    The latent dimension is chosen automatically by comparing canonical correlations
    with a permutation-null distribution. A dimension is kept only when its
    intervention alignment is stronger than what shuffled intervention assignments
    would normally produce.
    """

    def __init__(
        self,
        *,
        feature_count: int = 64,
        bandwidth: float = 1.5,
        ridge: float = 5e-2,
        permutations: int = 12,
        null_quantile: float = 0.95,
        min_correlation: float = 0.08,
        seed: int = 7,
    ) -> None:
        if feature_count < 4:
            raise ValueError("feature_count must be at least 4")
        if bandwidth <= 0 or ridge <= 0:
            raise ValueError("bandwidth and ridge must be positive")
        if permutations < 1:
            raise ValueError("permutations must be positive")
        if not 0.5 <= null_quantile < 1:
            raise ValueError("null_quantile must be in [0.5, 1)")
        self.feature_count = int(feature_count)
        self.bandwidth = float(bandwidth)
        self.ridge = float(ridge)
        self.permutations = int(permutations)
        self.null_quantile = float(null_quantile)
        self.min_correlation = float(min_correlation)
        self.seed = int(seed)
        self.result_: NonlinearOntologyResult | None = None

    def _fit_feature_map(
        self,
        x: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        input_mean, input_scale = _safe_scale(x)
        xs = (x - input_mean) / input_scale
        rng = np.random.default_rng(self.seed)
        weights = rng.normal(
            0.0,
            1.0 / self.bandwidth,
            size=(x.shape[1], self.feature_count),
        )
        bias = rng.uniform(0.0, 2.0 * np.pi, size=self.feature_count)
        fourier = np.sqrt(2.0 / self.feature_count) * np.cos(xs @ weights + bias)
        phi = np.column_stack([xs, fourier])
        feature_mean, feature_scale = _safe_scale(phi)
        standardized = (phi - feature_mean) / feature_scale
        return (
            standardized,
            input_mean,
            input_scale,
            weights,
            bias,
            feature_mean,
            feature_scale,
        )

    def _canonical_spectrum(
        self,
        phi: np.ndarray,
        interventions: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        u = np.asarray(interventions, dtype=float)
        if u.ndim == 1:
            u = u[:, None]
        u_mean, u_scale = _safe_scale(u)
        us = (u - u_mean) / u_scale

        n = max(len(phi) - 1, 1)
        cxx = (phi.T @ phi) / n + self.ridge * np.eye(phi.shape[1])
        cuu = (us.T @ us) / n + self.ridge * np.eye(us.shape[1])
        cxu = (phi.T @ us) / n

        wx = _inverse_sqrt(cxx, self.ridge)
        wu = _inverse_sqrt(cuu, self.ridge)
        matrix = wx @ cxu @ wu
        left, singular, _ = np.linalg.svd(matrix, full_matrices=False)
        components = wx @ left

        norms = np.linalg.norm(components, axis=0)
        components = components / np.where(norms < 1e-12, 1.0, norms)
        return np.asarray(singular, dtype=float), np.asarray(components, dtype=float)

    def fit(
        self,
        x: np.ndarray,
        interventions: np.ndarray,
    ) -> NonlinearOntologyResult:
        x = np.asarray(x, dtype=float)
        u = np.asarray(interventions, dtype=float)
        if x.ndim != 2:
            raise ValueError("x must be a 2D array")
        if u.ndim == 1:
            u = u[:, None]
        if u.ndim != 2 or len(x) != len(u):
            raise ValueError("interventions must have one row per observation")
        if len(x) < 24:
            raise ValueError("at least 24 observations are required")
        if u.shape[1] < 1:
            raise ValueError("at least one intervention descriptor is required")

        (
            phi,
            input_mean,
            input_scale,
            weights,
            bias,
            feature_mean,
            feature_scale,
        ) = self._fit_feature_map(x)
        correlations, components = self._canonical_spectrum(phi, u)

        rng = np.random.default_rng(self.seed + 91_177)
        null = np.zeros((self.permutations, len(correlations)), dtype=float)
        for index in range(self.permutations):
            permuted = u[rng.permutation(len(u))]
            null[index], _ = self._canonical_spectrum(phi, permuted)

        thresholds = np.quantile(null, self.null_quantile, axis=0)
        significant = correlations > np.maximum(thresholds, self.min_correlation)
        selected_dim = int(np.sum(significant))
        selected_dim = max(1, selected_dim)

        result = NonlinearOntologyResult(
            input_mean=input_mean,
            input_scale=input_scale,
            random_weights=weights,
            random_bias=bias,
            feature_mean=feature_mean,
            feature_scale=feature_scale,
            components=components,
            canonical_correlations=correlations,
            null_thresholds=np.asarray(thresholds, dtype=float),
            selected_dim=selected_dim,
            bandwidth=self.bandwidth,
        )
        self.result_ = result
        return result

    def transform(
        self,
        x: np.ndarray,
        n_components: int | None = None,
    ) -> np.ndarray:
        if self.result_ is None:
            raise RuntimeError("fit must be called before transform")
        return self.result_.transform(x, n_components=n_components)

    def fit_transform(
        self,
        x: np.ndarray,
        interventions: np.ndarray,
    ) -> np.ndarray:
        return self.fit(x, interventions).transform(x)
