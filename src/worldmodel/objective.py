from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ScientificObjectiveTerms:
    prediction_error: float
    description_length: float
    invariance_penalty: float
    calibration_penalty: float
    posterior_entropy: float
    expected_information_gain: float
    experiment_cost: float
    performative_feedback: float
    unknown_mass: float


@dataclass(frozen=True)
class ScientificObjectiveResult:
    total: float
    terms: ScientificObjectiveTerms


class FalsifiableCausalCompressionObjective:
    """Unified score for compact, falsifiable and intervention-stable theories.

    Lower is better:

      log predictive error
      + complexity
      + invariance/calibration penalties
      + unresolved posterior entropy
      + cost and performative feedback
      + misspecification mass
      - value of the next falsifying observation
    """

    def __init__(
        self,
        *,
        complexity_weight: float = 0.04,
        invariance_weight: float = 0.25,
        calibration_weight: float = 0.15,
        entropy_weight: float = 0.20,
        information_gain_weight: float = 0.35,
        cost_weight: float = 0.10,
        feedback_weight: float = 0.25,
        unknown_weight: float = 0.30,
    ) -> None:
        self.complexity_weight = float(complexity_weight)
        self.invariance_weight = float(invariance_weight)
        self.calibration_weight = float(calibration_weight)
        self.entropy_weight = float(entropy_weight)
        self.information_gain_weight = float(information_gain_weight)
        self.cost_weight = float(cost_weight)
        self.feedback_weight = float(feedback_weight)
        self.unknown_weight = float(unknown_weight)

    def score(self, terms: ScientificObjectiveTerms) -> ScientificObjectiveResult:
        total = (
            np.log(max(float(terms.prediction_error), 1e-12))
            + self.complexity_weight * float(terms.description_length)
            + self.invariance_weight * float(terms.invariance_penalty)
            + self.calibration_weight * float(terms.calibration_penalty)
            + self.entropy_weight * float(terms.posterior_entropy)
            - self.information_gain_weight * float(terms.expected_information_gain)
            + self.cost_weight * float(terms.experiment_cost)
            + self.feedback_weight * float(terms.performative_feedback)
            + self.unknown_weight * float(terms.unknown_mass)
        )
        return ScientificObjectiveResult(total=float(total), terms=terms)
