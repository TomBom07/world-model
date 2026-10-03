from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class OntologyResult:
    mean: np.ndarray
    scale: np.ndarray
    components: np.ndarray
    eigenvalues: np.ndarray
    environments: tuple[str, ...]
    separation_score: float

    @property
    def latent_dim(self) -> int:
        return int(self.components.shape[1])

    def transform(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        standardized = (x - self.mean) / self.scale
        return standardized @ self.components


class CausalOntologyLearner:
    """Discover intervention-relevant latent coordinates.

    The learner searches for a low-dimensional subspace whose coordinates change
    systematically across environments/interventions while suppressing variation
    that is large inside an environment.  It is intentionally small and auditable:
    a generalized eigenproblem rather than an opaque end-to-end network.

    This is a first causal-coarse-graining primitive, not a claim that arbitrary
    nonlinear ontologies are solved.
    """

    def __init__(self, n_components: int = 2, ridge: float = 1e-3) -> None:
        if n_components < 1:
            raise ValueError("n_components must be positive")
        if ridge <= 0:
            raise ValueError("ridge must be positive")
        self.n_components = int(n_components)
        self.ridge = float(ridge)
        self.result_: OntologyResult | None = None

    def fit(self, x: np.ndarray, environments: np.ndarray) -> OntologyResult:
        x = np.asarray(x, dtype=float)
        environments = np.asarray(environments)
        if x.ndim != 2:
            raise ValueError("x must be a 2D array")
        if len(x) != len(environments):
            raise ValueError("x and environments must have the same number of rows")
        if len(x) < max(12, self.n_components * 4):
            raise ValueError("not enough observations for ontology learning")

        mean = x.mean(axis=0)
        scale = x.std(axis=0)
        scale = np.where(scale < 1e-8, 1.0, scale)
        xs = (x - mean) / scale

        labels = tuple(str(v) for v in np.unique(environments))
        if len(labels) < 2:
            raise ValueError("at least two environments/interventions are required")

        overall = xs.mean(axis=0)
        d = xs.shape[1]
        between = np.zeros((d, d), dtype=float)
        within = np.zeros((d, d), dtype=float)

        for raw_label in np.unique(environments):
            group = xs[environments == raw_label]
            if len(group) < 2:
                continue
            delta = group.mean(axis=0) - overall
            between += len(group) * np.outer(delta, delta)
            centered = group - group.mean(axis=0)
            within += centered.T @ centered

        between /= max(len(xs), 1)
        within /= max(len(xs) - len(labels), 1)
        within += self.ridge * np.eye(d)

        # Symmetric whitening keeps the generalized eigenproblem numerically stable.
        w_vals, w_vecs = np.linalg.eigh(within)
        w_vals = np.clip(w_vals, self.ridge, None)
        inv_sqrt = (w_vecs * (1.0 / np.sqrt(w_vals))) @ w_vecs.T
        whitened = inv_sqrt @ between @ inv_sqrt
        whitened = 0.5 * (whitened + whitened.T)

        eigvals, eigvecs = np.linalg.eigh(whitened)
        order = np.argsort(eigvals)[::-1]
        k = min(self.n_components, d)
        selected = order[:k]
        components = inv_sqrt @ eigvecs[:, selected]

        # Normalize each discovered coordinate for stable downstream use.
        norms = np.linalg.norm(components, axis=0)
        components = components / np.where(norms < 1e-12, 1.0, norms)

        z = xs @ components
        between_z = 0.0
        within_z = 0.0
        z_mean = z.mean(axis=0)
        for raw_label in np.unique(environments):
            group = z[environments == raw_label]
            delta = group.mean(axis=0) - z_mean
            between_z += len(group) * float(delta @ delta)
            within_z += float(np.sum((group - group.mean(axis=0)) ** 2))
        separation = between_z / max(within_z, 1e-12)

        result = OntologyResult(
            mean=mean,
            scale=scale,
            components=components,
            eigenvalues=np.asarray(eigvals[selected], dtype=float),
            environments=labels,
            separation_score=float(separation),
        )
        self.result_ = result
        return result

    def transform(self, x: np.ndarray) -> np.ndarray:
        if self.result_ is None:
            raise RuntimeError("fit must be called before transform")
        return self.result_.transform(x)

    def fit_transform(self, x: np.ndarray, environments: np.ndarray) -> np.ndarray:
        return self.fit(x, environments).transform(x)
