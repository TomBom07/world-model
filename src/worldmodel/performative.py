from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .experiment_design import (
    ExperimentCandidate,
    ExpectedInformationGainSelector,
)


@dataclass(frozen=True)
class PerformativeObservation:
    structural: np.ndarray
    feedback_shift: np.ndarray
    observed: np.ndarray


class PerformativeWorld:
    """A tiny reflexive environment where publishing a prediction changes outcomes."""

    def __init__(self, *, sensitivity: float = 0.5) -> None:
        self.sensitivity = float(sensitivity)

    def observe(
        self,
        candidate: ExperimentCandidate,
        *,
        true_hypothesis: str,
        published_prediction: np.ndarray,
    ) -> PerformativeObservation:
        if true_hypothesis not in candidate.predictions:
            raise ValueError("unknown true_hypothesis")
        structural = np.asarray(candidate.predictions[true_hypothesis], dtype=float)
        published = np.asarray(published_prediction, dtype=float)
        if published.shape != structural.shape:
            raise ValueError("published_prediction shape mismatch")
        shift = self.sensitivity * float(candidate.feedback) * np.tanh(published)
        return PerformativeObservation(
            structural=structural,
            feedback_shift=shift,
            observed=structural + shift,
        )


def compare_naive_and_feedback_aware_selection(
    candidates: list[ExperimentCandidate],
    prior: dict[str, float],
    *,
    sigma: float = 0.15,
    seed: int = 7,
    feedback_weight: float = 0.8,
) -> dict[str, object]:
    naive = ExpectedInformationGainSelector(
        sigma=sigma,
        samples_per_hypothesis=128,
        seed=seed,
    ).score(candidates, prior)
    aware = ExpectedInformationGainSelector(
        sigma=sigma,
        samples_per_hypothesis=128,
        seed=seed,
        feedback_weight=feedback_weight,
    ).score(candidates, prior)
    return {
        "naive": naive,
        "feedback_aware": aware,
        "changed_choice": bool(
            naive and aware and naive[0].name != aware[0].name
        ),
    }
