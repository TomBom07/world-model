from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def entropy(weights: dict[str, float]) -> float:
    values = np.asarray([v for v in weights.values() if v > 0], dtype=float)
    return float(-np.sum(values * np.log(values))) if len(values) else 0.0


def _normalize_prior(prior: dict[str, float], hypotheses: tuple[str, ...]) -> dict[str, float]:
    raw = np.asarray([max(float(prior.get(h, 0.0)), 0.0) for h in hypotheses])
    total = float(raw.sum())
    if total <= 0:
        raw = np.ones(len(hypotheses), dtype=float)
        total = float(raw.sum())
    raw /= total
    return {h: float(p) for h, p in zip(hypotheses, raw)}


def gaussian_posterior(
    prior: dict[str, float],
    observation: np.ndarray,
    predictions: dict[str, np.ndarray],
    sigma: float,
) -> dict[str, float]:
    hypotheses = tuple(predictions)
    prior = _normalize_prior(prior, hypotheses)
    y = np.asarray(observation, dtype=float)
    s = max(float(sigma), 1e-9)
    logw = []
    for h in hypotheses:
        mu = np.asarray(predictions[h], dtype=float)
        error = (y - mu) / s
        logw.append(np.log(max(prior[h], 1e-300)) - 0.5 * float(error @ error))
    logw = np.asarray(logw)
    logw -= logw.max()
    w = np.exp(np.clip(logw, -745, 0))
    w /= w.sum()
    return {h: float(p) for h, p in zip(hypotheses, w)}


@dataclass(frozen=True)
class ExperimentCandidate:
    name: str
    predictions: dict[str, np.ndarray]
    cost: float = 0.0
    risk: float = 0.0
    feedback: float = 0.0


@dataclass(frozen=True)
class ExperimentScore:
    name: str
    expected_information_gain: float
    utility: float
    expected_entropy_after: float
    cost: float
    risk: float
    feedback: float


class ExpectedInformationGainSelector:
    """Choose observations by expected posterior entropy reduction."""

    def __init__(
        self,
        *,
        sigma: float = 0.08,
        samples_per_hypothesis: int = 128,
        seed: int = 7,
        cost_weight: float = 0.0,
        risk_weight: float = 0.0,
        feedback_weight: float = 0.0,
    ) -> None:
        self.sigma = float(sigma)
        self.samples_per_hypothesis = int(samples_per_hypothesis)
        self.seed = int(seed)
        self.cost_weight = float(cost_weight)
        self.risk_weight = float(risk_weight)
        self.feedback_weight = float(feedback_weight)

    def score(
        self,
        candidates: list[ExperimentCandidate],
        prior: dict[str, float],
    ) -> list[ExperimentScore]:
        if not candidates:
            return []
        hypotheses = tuple(candidates[0].predictions)
        normalized_prior = _normalize_prior(prior, hypotheses)
        h_before = entropy(normalized_prior)
        rng = np.random.default_rng(self.seed)
        scored: list[ExperimentScore] = []

        for candidate in candidates:
            if tuple(candidate.predictions) != hypotheses:
                raise ValueError("all candidates must contain the same hypotheses")
            expected_h = 0.0
            for h in hypotheses:
                p_h = normalized_prior[h]
                if p_h <= 0:
                    continue
                mu = np.asarray(candidate.predictions[h], dtype=float)
                noise = rng.normal(
                    0.0,
                    self.sigma,
                    size=(self.samples_per_hypothesis, len(mu)),
                )
                for sample in mu + noise:
                    post = gaussian_posterior(
                        normalized_prior,
                        sample,
                        candidate.predictions,
                        self.sigma,
                    )
                    expected_h += (
                        p_h
                        * entropy(post)
                        / max(self.samples_per_hypothesis, 1)
                    )

            ig = max(0.0, h_before - expected_h)
            utility = (
                ig
                - self.cost_weight * float(candidate.cost)
                - self.risk_weight * float(candidate.risk)
                - self.feedback_weight * float(candidate.feedback)
            )
            scored.append(
                ExperimentScore(
                    name=candidate.name,
                    expected_information_gain=float(ig),
                    utility=float(utility),
                    expected_entropy_after=float(expected_h),
                    cost=float(candidate.cost),
                    risk=float(candidate.risk),
                    feedback=float(candidate.feedback),
                )
            )

        return sorted(scored, key=lambda item: item.utility, reverse=True)
