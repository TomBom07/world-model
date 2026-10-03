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
    """Compile executable transition laws in a learned latent state space."""

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
        train_fraction: float = 0.7,
    ) -> LatentLawResult:
        z = np.asarray(z, dtype=float)
        if z.ndim != 2 or len(z) < 40:
            raise ValueError("z must be a 2D trajectory with at least 40 rows")
        if not 0.5 <= train_fraction < 0.9:
            raise ValueError("train_fraction must be in [0.5, 0.9)")

        x = z[:-1]
        delta = z[1:] - z[:-1]
        split = max(24, int(len(x) * train_fraction))
        split = min(split, len(x) - 8)
        names = [f"z{i}" for i in range(z.shape[1])]
        compiler = MechanismCompiler(
            max_terms=self.max_terms,
            beam_width=self.beam_width,
            top_k=self.top_k,
            interactions=True,
            squares=True,
        )

        laws: list[LatentLaw] = []
        for target_index, target_name in enumerate(names):
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

    Candidate latent dimensions are scored by a small falsifiable objective:
    held-out transition error + description-length pressure - intervention signal.
    This is the first place in WorldModel where the representation and the executable
    dynamics are selected together rather than as independent stages.
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
        ontology = self.ontology_learner.fit(x, interventions)
        max_dim = min(ontology.max_dim, max(1, interventions.shape[1]))
        candidates: list[tuple[int, float, LatentLawResult]] = []

        for k in range(1, max_dim + 1):
            z = ontology.transform(x, n_components=k)
            law = self.law_compiler.fit(z)
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
