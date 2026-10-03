from __future__ import annotations

from dataclasses import dataclass
from math import log, pi

import numpy as np


UNKNOWN = "__unknown__"


@dataclass(frozen=True)
class OpenWorldUpdate:
    posterior: dict[str, float]
    unknown_probability: float
    best_known: str
    best_known_probability: float
    surprise: float


class OpenWorldBayes:
    """Bayesian update with explicit probability mass for model misspecification.

    Known mechanisms use a narrow Gaussian observation model.  The unknown model
    uses a broader heavy-tailed Cauchy likelihood around the ensemble prediction,
    allowing sufficiently surprising observations to move posterior mass to
    'none of the above'.
    """

    def __init__(
        self,
        *,
        sigma: float = 0.08,
        unknown_scale: float = 8.0,
        unknown_prior: float = 0.05,
    ) -> None:
        if sigma <= 0 or unknown_scale <= 1 or not 0 < unknown_prior < 1:
            raise ValueError("invalid open-world parameters")
        self.sigma = float(sigma)
        self.unknown_scale = float(unknown_scale)
        self.unknown_prior = float(unknown_prior)

    def update(
        self,
        *,
        prior: dict[str, float],
        observation: np.ndarray,
        predictions: dict[str, np.ndarray],
    ) -> OpenWorldUpdate:
        if not predictions:
            raise ValueError("at least one known mechanism is required")
        hypotheses = tuple(predictions)
        raw = np.asarray([max(float(prior.get(h, 0.0)), 0.0) for h in hypotheses])
        if raw.sum() <= 0:
            raw = np.ones(len(hypotheses), dtype=float)
        raw /= raw.sum()
        raw *= 1.0 - self.unknown_prior

        y = np.asarray(observation, dtype=float)
        sigma = self.sigma
        log_weights: dict[str, float] = {}
        log_norm = len(y) * log(sigma * np.sqrt(2.0 * pi))

        for h, p in zip(hypotheses, raw):
            mu = np.asarray(predictions[h], dtype=float)
            error = (y - mu) / sigma
            log_weights[h] = log(max(float(p), 1e-300)) - 0.5 * float(error @ error) - log_norm

        ensemble_mean = np.mean(
            np.vstack([np.asarray(predictions[h], dtype=float) for h in hypotheses]),
            axis=0,
        )
        cauchy_scale = sigma * self.unknown_scale
        standardized = (y - ensemble_mean) / cauchy_scale
        unknown_log_like = -float(
            np.sum(np.log(pi * cauchy_scale * (1.0 + standardized * standardized)))
        )
        log_weights[UNKNOWN] = log(self.unknown_prior) + unknown_log_like

        maximum = max(log_weights.values())
        weights = {k: np.exp(v - maximum) for k, v in log_weights.items()}
        normalizer = float(sum(weights.values()))
        posterior = {k: float(v / normalizer) for k, v in weights.items()}

        known = {h: posterior[h] for h in hypotheses}
        best_known = max(known, key=known.get)
        # Negative log evidence up to a common constant; useful as a relative surprise score.
        surprise = float(-(maximum + log(normalizer)))
        return OpenWorldUpdate(
            posterior=posterior,
            unknown_probability=float(posterior[UNKNOWN]),
            best_known=best_known,
            best_known_probability=float(known[best_known]),
            surprise=surprise,
        )
