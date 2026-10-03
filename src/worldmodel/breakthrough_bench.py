from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

from .experiment_design import ExperimentCandidate, ExpectedInformationGainSelector
from .ontology_learning import CausalOntologyLearner
from .open_world import OpenWorldBayes
from .scientific_sealing import seal_scientific_claim


def _latent_recovery_score(coordinates: np.ndarray, truth: np.ndarray) -> float:
    model = LinearRegression().fit(coordinates, truth)
    predicted = model.predict(coordinates)
    return float(r2_score(truth, predicted, multioutput="variance_weighted"))


def generate_hidden_ontology_problem(
    *,
    seed: int = 7,
    samples_per_environment: int = 180,
    observed_dim: int = 12,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create hidden causal coordinates buried under stronger nuisance variation."""
    if observed_dim < 6:
        raise ValueError("observed_dim must be at least 6")
    rng = np.random.default_rng(seed)
    effects = np.array(
        [
            [0.0, 0.0],
            [1.6, 0.1],
            [0.1, -1.5],
            [1.2, 1.0],
        ],
        dtype=float,
    )
    mixing = rng.normal(size=(observed_dim, 2))
    mixing /= np.linalg.norm(mixing, axis=0, keepdims=True)

    xs: list[np.ndarray] = []
    zs: list[np.ndarray] = []
    envs: list[int] = []
    for env, effect in enumerate(effects):
        z = effect + rng.normal(0, 0.45, size=(samples_per_environment, 2))
        causal_signal = z @ mixing.T

        # Large environment-independent nuisance deliberately dominates raw variance.
        nuisance = rng.normal(0, 3.0, size=(samples_per_environment, observed_dim))
        nuisance_direction = rng.normal(size=(observed_dim,))
        nuisance_direction /= np.linalg.norm(nuisance_direction)
        nuisance_scalar = rng.normal(0, 4.0, size=(samples_per_environment, 1))
        x = causal_signal + 0.50 * nuisance + nuisance_scalar * nuisance_direction

        xs.append(x)
        zs.append(z)
        envs.extend([env] * samples_per_environment)

    return np.vstack(xs), np.vstack(zs), np.asarray(envs)


def run_breakthrough_benchmark(seed: int = 7) -> dict[str, object]:
    x, truth, environments = generate_hidden_ontology_problem(seed=seed)

    causal = CausalOntologyLearner(n_components=2, ridge=5e-3)
    causal_coords = causal.fit_transform(x, environments)
    causal_score = _latent_recovery_score(causal_coords, truth)

    pca_coords = PCA(n_components=2, random_state=seed).fit_transform(x)
    pca_score = _latent_recovery_score(pca_coords, truth)

    candidates = [
        ExperimentCandidate(
            "weak_probe",
            {
                "mechanism_a": np.array([0.1, 0.1]),
                "mechanism_b": np.array([0.15, 0.12]),
            },
        ),
        ExperimentCandidate(
            "diagnostic_probe",
            {
                "mechanism_a": np.array([1.0, -0.8]),
                "mechanism_b": np.array([-0.9, 0.85]),
            },
        ),
    ]
    eig = ExpectedInformationGainSelector(
        sigma=0.12,
        samples_per_hypothesis=160,
        seed=seed + 1,
    ).score(candidates, {"mechanism_a": 0.5, "mechanism_b": 0.5})

    open_world = OpenWorldBayes(
        sigma=0.12,
        unknown_scale=10.0,
        unknown_prior=0.08,
    )
    familiar = open_world.update(
        prior={"mechanism_a": 0.5, "mechanism_b": 0.5},
        observation=np.array([1.02, -0.77]),
        predictions=candidates[1].predictions,
    )
    alien = open_world.update(
        prior={"mechanism_a": 0.5, "mechanism_b": 0.5},
        observation=np.array([4.5, 4.2]),
        predictions=candidates[1].predictions,
    )

    ontology_result = causal.result_
    assert ontology_result is not None

    selected = eig[0]
    now = datetime.now(timezone.utc)
    claim = seal_scientific_claim(
        experiment_name="open-mechanism-bench-v1",
        code_ref="worldmodel-v3-causal-renormalization",
        data_cutoff=now,
        created_at=now,
        ontology={
            "latent_dim": ontology_result.latent_dim,
            "separation_score": ontology_result.separation_score,
            "eigenvalues": ontology_result.eigenvalues.tolist(),
        },
        hypotheses={
            "mechanism_a": "first candidate mechanism",
            "mechanism_b": "second candidate mechanism",
            "__unknown__": "none of the above",
        },
        posterior=familiar.posterior,
        selected_query=asdict(selected),
        preregistered_predictions={
            c.name: {k: v.tolist() for k, v in c.predictions.items()}
            for c in candidates
        },
        evaluation_protocol={
            "primary": "latent recovery R2 and expected information gain",
            "baseline": "PCA",
            "unknown_challenge": "far-out observation must increase unknown posterior",
        },
    )

    return {
        "ontology": {
            "causal_latent_recovery_r2": causal_score,
            "pca_latent_recovery_r2": pca_score,
            "improvement_over_pca": causal_score - pca_score,
            "intervention_separation": ontology_result.separation_score,
            "eigenvalues": ontology_result.eigenvalues.tolist(),
        },
        "experiment_design": [asdict(item) for item in eig],
        "open_world": {
            "familiar_observation": asdict(familiar),
            "alien_observation": asdict(alien),
        },
        "scientific_seal": {
            "seal": claim.seal,
            "valid": claim.verify(),
        },
        "interpretation": (
            "This benchmark tests a narrow but falsifiable V3 claim: intervention-aware "
            "coarse-graining should recover causally relevant latent coordinates better "
            "than variance-only PCA when nuisance variance dominates. It does not prove "
            "general causal ontology discovery."
        ),
    }
