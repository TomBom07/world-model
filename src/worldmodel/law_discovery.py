from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import r2_score

from .compiler import MechanismCompiler
from .nonlinear_ontology import InterventionAwareOntologyLearner, NonlinearOntologyResult


@dataclass(frozen=True)
class LatentLaw:
    target: str
    program: str
    terms: tuple[str, ...]
    validation_mse: float
    validation_r2: float
    complexity: int


@dataclass(frozen=True)
class LatentLawResult:
    laws: tuple[LatentLaw, ...]
    mean_validation_mse: float
    mean_validation_r2: float
    total_complexity: int


class LatentLawCompiler:
    """Compile executable transition laws in a learned latent state space.

    Optional control variables are treated as observed interventions that can drive
    the state transition. This matters for scientific systems where the state law is
    not autonomous because an experimenter or environment is actively perturbing it.
    """

    def __init__(
        self,
        *,
        max_terms: int = 4,
        beam_width: int = 32,
        top_k: int = 12,
    ) -> None:
        self.max_terms = int(max_terms)
        self.beam_width = int(beam_width)
        self.top_k = int(top_k)

    def fit(
        self,
        z: np.ndarray,
        *,
        controls: np.ndarray | None = None,
        train_fraction: float = 0.7,
    ) -> LatentLawResult:
        z = np.asarray(z, dtype=float)
        if z.ndim != 2 or len(z) < 40:
            raise ValueError("z must be a 2D trajectory with at least 40 rows")
        if not 0.5 <= train_fraction < 0.9:
            raise ValueError("train_fraction must be in [0.5, 0.9)")

        state = z[:-1]
        delta = z[1:] - z[:-1]
        state_names = [f"z{i}" for i in range(z.shape[1])]

        if controls is not None:
            controls = np.asarray(controls, dtype=float)
            if controls.ndim == 1:
                controls = controls[:, None]
            if controls.ndim != 2:
                raise ValueError("controls must be a 2D array")
            if len(controls) == len(z):
                transition_controls = controls[:-1]
            elif len(controls) == len(z) - 1:
                transition_controls = controls
            else:
                raise ValueError("controls must have len(z) or len(z)-1 rows")
            x = np.column_stack([state, transition_controls])
            control_names = [f"u{i}" for i in range(transition_controls.shape[1])]
            names = state_names + control_names
        else:
            x = state
            names = state_names

        split = max(24, int(len(x) * train_fraction))
        split = min(split, len(x) - 8)
        compiler = MechanismCompiler(
            max_terms=self.max_terms,
            beam_width=self.beam_width,
            top_k=self.top_k,
            interactions=True,
            squares=True,
        )

        laws: list[LatentLaw] = []
        for target_index, target_name in enumerate(state_names):
            result = compiler.fit(
                x[:split],
                delta[:split, target_index],
                names,
            )
            model = result.best
            prediction = model.predict(x[split:])
            truth = delta[split:, target_index]
            mse = float(np.mean((truth - prediction) ** 2))
            baseline = float(np.mean((truth - truth.mean()) ** 2))
            r2 = float(r2_score(truth, prediction)) if baseline > 1e-12 else 0.0
            laws.append(
                LatentLaw(
                    target=f"d{target_name}/dt",
                    program=model.as_program(),
                    terms=model.term_names,
                    validation_mse=mse,
                    validation_r2=r2,
                    complexity=model.complexity,
                )
            )

        return LatentLawResult(
            laws=tuple(laws),
            mean_validation_mse=float(np.mean([law.validation_mse for law in laws])),
            mean_validation_r2=float(np.mean([law.validation_r2 for law in laws])),
            total_complexity=int(sum(law.complexity for law in laws)),
        )


@dataclass(frozen=True)
class JointDiscoveryResult:
    ontology: NonlinearOntologyResult
    selected_dim: int
    law_result: LatentLawResult
    objective: float
    candidate_objectives: tuple[tuple[int, float], ...]


class JointOntologyLawLearner:
    """Select ontology size using both intervention alignment and law simplicity.

    Candidate latent dimensions are scored by a compact falsifiable objective:
    held-out transition error + description-length pressure - intervention signal.
    Dimensions that pass the ontology learner's permutation-null significance test
    form a hard lower bound, so compression cannot erase intervention-supported
    causal coordinates. This couples representation and executable dynamics without
    treating statistically supported structure as optional.
    """

    def __init__(
        self,
        ontology_learner: InterventionAwareOntologyLearner | None = None,
        law_compiler: LatentLawCompiler | None = None,
        *,
        complexity_weight: float = 0.015,
        intervention_weight: float = 0.08,
    ) -> None:
        self.ontology_learner = ontology_learner or InterventionAwareOntologyLearner()
        self.law_compiler = law_compiler or LatentLawCompiler()
        self.complexity_weight = float(complexity_weight)
        self.intervention_weight = float(intervention_weight)

    def fit(
        self,
        x: np.ndarray,
        interventions: np.ndarray,
    ) -> JointDiscoveryResult:
        interventions = np.asarray(interventions, dtype=float)
        if interventions.ndim == 1:
            interventions = interventions[:, None]
        ontology = self.ontology_learner.fit(x, interventions)
        max_dim = min(ontology.max_dim, max(1, interventions.shape[1]))
        # A coordinate that already beats the permutation-null intervention test is
        # causal evidence, not optional description length. The joint dynamics stage
        # may retain or add supported coordinates, but must not erase a statistically
        # intervention-relevant axis merely because a smaller model compresses better.
        min_dim = min(max_dim, max(1, ontology.selected_dim))
        candidates: list[tuple[int, float, LatentLawResult]] = []

        for k in range(min_dim, max_dim + 1):
            z = ontology.transform(x, n_components=k)
            law = self.law_compiler.fit(z, controls=interventions)
            signal = float(np.sum(ontology.canonical_correlations[:k] ** 2))
            objective = (
                np.log(max(law.mean_validation_mse, 1e-12))
                + self.complexity_weight * law.total_complexity
                - self.intervention_weight * signal
            )
            candidates.append((k, float(objective), law))

        selected_dim, objective, law_result = min(candidates, key=lambda item: item[1])
        return JointDiscoveryResult(
            ontology=ontology,
            selected_dim=int(selected_dim),
            law_result=law_result,
            objective=float(objective),
            candidate_objectives=tuple((k, score) for k, score, _ in candidates),
        )
