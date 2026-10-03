from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone

import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from sklearn.metrics import adjusted_rand_score, r2_score

from .experiment_design import ExperimentCandidate
from .law_discovery import JointOntologyLawLearner, LatentLawCompiler
from .natural_experiments import NaturalEnvironmentDiscoverer
from .nonlinear_ontology import InterventionAwareOntologyLearner
from .objective import (
    FalsifiableCausalCompressionObjective,
    ScientificObjectiveTerms,
)
from .ontology_evolution import OntologyEvolutionDetector
from .open_world import OpenWorldBayes
from .performative import compare_naive_and_feedback_aware_selection
from .prospective import create_prospective_entry, score_prospective_entry
from .theory_invention import ResidualTheoryInventor


def _latent_recovery_score(coordinates: np.ndarray, truth: np.ndarray) -> float:
    model = LinearRegression().fit(coordinates, truth)
    predicted = model.predict(coordinates)
    return float(r2_score(truth, predicted, multioutput="variance_weighted"))


def _domain_problem(
    domain: str,
    *,
    seed: int,
    samples_per_environment: int = 120,
    observed_dim: int = 12,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    interventions = np.array(
        [
            [-1.5, -1.1],
            [-1.5, 1.1],
            [0.0, 0.0],
            [1.5, -1.1],
            [1.5, 1.1],
            [0.0, 1.7],
        ],
        dtype=float,
    )
    mixing = rng.normal(size=(7, observed_dim))
    nuisance_direction = rng.normal(size=observed_dim)
    nuisance_direction /= np.linalg.norm(nuisance_direction)

    xs: list[np.ndarray] = []
    zs: list[np.ndarray] = []
    us: list[np.ndarray] = []

    for intervention in interventions:
        z = intervention + rng.normal(
            0.0,
            0.32,
            size=(samples_per_environment, 2),
        )
        a, b = z[:, 0], z[:, 1]

        if domain == "physics":
            features = np.column_stack(
                [
                    a + 0.25 * a**3,
                    b + 0.20 * b**3,
                    np.sin(a),
                    np.cos(b),
                    a * b,
                    a**2,
                    b**2,
                ]
            )
        elif domain == "ecology":
            features = np.column_stack(
                [
                    np.exp(0.30 * a),
                    np.exp(0.30 * b),
                    a * b,
                    np.sin(0.7 * a),
                    np.sin(0.7 * b),
                    a**2,
                    b**2,
                ]
            )
        elif domain == "epidemic":
            sigmoid_a = 1.0 / (1.0 + np.exp(-a))
            sigmoid_b = 1.0 / (1.0 + np.exp(-b))
            features = np.column_stack(
                [
                    sigmoid_a,
                    sigmoid_b,
                    1.0 / (1.0 + np.exp(-(a + b))),
                    a * b,
                    np.tanh(a),
                    np.tanh(b),
                    a**2 - b**2,
                ]
            )
        else:
            raise ValueError(f"unknown domain: {domain}")

        x = (
            features @ mixing
            + rng.normal(0.0, 1.5, size=(samples_per_environment, observed_dim))
            + rng.normal(0.0, 3.5, size=(samples_per_environment, 1))
            * nuisance_direction
        )
        xs.append(x)
        zs.append(z)
        us.append(
            np.repeat(
                intervention[None, :],
                samples_per_environment,
                axis=0,
            )
        )

    return np.vstack(xs), np.vstack(zs), np.vstack(us)


def _natural_regime_problem(
    *,
    seed: int,
    regime_length: int = 96,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    means = np.array(
        [
            [-2.2, 0.2, 0.0, 1.1],
            [0.0, 2.1, -1.2, 0.1],
            [2.0, -0.4, 1.4, -1.0],
            [0.4, -2.0, -0.2, 1.8],
        ],
        dtype=float,
    )
    xs = []
    labels = []
    for index, mean in enumerate(means):
        xs.append(rng.normal(mean, 0.45, size=(regime_length, len(mean))))
        labels.extend([index] * regime_length)
    return np.vstack(xs), np.asarray(labels, dtype=int)


def _henon_trajectory(*, seed: int, n: int = 420) -> np.ndarray:
    rng = np.random.default_rng(seed)
    z = np.zeros((n, 2), dtype=float)
    z[0] = np.array([0.1, 0.1], dtype=float)
    for t in range(n - 1):
        x, y = z[t]
        z[t + 1] = np.array(
            [
                1.0 - 1.2 * x * x + y,
                0.30 * x,
            ]
        ) + rng.normal(0.0, 0.002, size=2)
    return z


def _controlled_joint_problem(
    *,
    seed: int,
    n: int = 420,
    observed_dim: int = 8,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    prototypes = np.array(
        [
            [-1.0, -0.8],
            [1.0, -0.8],
            [1.0, 0.9],
            [-1.0, 0.9],
        ],
        dtype=float,
    )
    controls = np.zeros((n, 2), dtype=float)
    block = 42
    for t in range(n):
        controls[t] = prototypes[(t // block) % len(prototypes)]

    z = np.zeros((n, 2), dtype=float)
    z[0] = np.array([0.15, -0.10])
    for t in range(n - 1):
        a, b = z[t]
        u0, u1 = controls[t]
        z[t + 1, 0] = (
            0.66 * a
            + 0.11 * b
            + 0.23 * u0
            + 0.055 * a * b
        )
        z[t + 1, 1] = (
            -0.09 * a
            + 0.69 * b
            + 0.21 * u1
            - 0.045 * a * a
        )
        z[t + 1] += rng.normal(0.0, 0.008, size=2)

    mixing = rng.normal(size=(2, observed_dim))
    nuisance = rng.normal(size=observed_dim)
    nuisance /= np.linalg.norm(nuisance)
    x = (
        z @ mixing
        + rng.normal(0.0, 0.10, size=(n, observed_dim))
        + rng.normal(0.0, 0.25, size=(n, 1)) * nuisance
    )
    return x, z, controls


def _theory_invention_benchmark(seed: int) -> dict[str, object]:
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(360, 3))
    y = (
        0.3
        + 0.6 * x[:, 0]
        + 1.5 * x[:, 0] * x[:, 1]
        - 0.7 * x[:, 2] ** 2
        + rng.normal(0.0, 0.08, size=len(x))
    )
    baseline = 0.3 + 0.6 * x[:, 0]

    sample = slice(-18, None)
    predictions = {
        "linear_incumbent": baseline[sample],
        "null_incumbent": np.zeros(18, dtype=float),
    }
    open_world = OpenWorldBayes(
        sigma=0.16,
        unknown_scale=12.0,
        unknown_prior=0.08,
    ).update(
        prior={"linear_incumbent": 0.8, "null_incumbent": 0.2},
        observation=y[sample],
        predictions=predictions,
    )

    inventor = ResidualTheoryInventor(
        max_terms=4,
        min_relative_improvement=0.35,
    )
    theory = inventor.invent_if_unknown(
        unknown_probability=open_world.unknown_probability,
        x=x,
        y=y,
        baseline_prediction=baseline,
        feature_names=["x0", "x1", "x2"],
        threshold=0.5,
    )
    return {
        "open_world": asdict(open_world),
        "invented": asdict(theory) if theory is not None else None,
    }


def _ontology_evolution_benchmark(seed: int) -> dict[str, object]:
    rng = np.random.default_rng(seed)
    z0 = rng.normal(size=300)
    z1 = rng.normal(size=300)
    z2 = z1 + rng.normal(0.0, 0.01, size=300)
    z = np.column_stack([z0, z1, z2])
    residuals = np.where(z0 >= 0, 1.0, -1.0) + rng.normal(0.0, 0.12, size=300)

    result = OntologyEvolutionDetector(
        split_gain=0.25,
        merge_correlation=0.97,
        min_leaf=20,
    ).analyze(z, residuals)
    return {
        "splits": [asdict(item) for item in result.splits],
        "merges": [asdict(item) for item in result.merges],
    }


def _performative_benchmark(seed: int) -> dict[str, object]:
    candidates = [
        ExperimentCandidate(
            name="maximal_but_reflexive",
            predictions={
                "a": np.array([1.0, -1.0]),
                "b": np.array([-1.0, 1.0]),
            },
            feedback=1.0,
        ),
        ExperimentCandidate(
            name="slightly_weaker_low_feedback",
            predictions={
                "a": np.array([0.30, -0.20]),
                "b": np.array([-0.20, 0.30]),
            },
            feedback=0.03,
        ),
    ]
    comparison = compare_naive_and_feedback_aware_selection(
        candidates,
        {"a": 0.5, "b": 0.5},
        sigma=0.18,
        seed=seed,
        feedback_weight=0.50,
    )
    return {
        "naive": [asdict(item) for item in comparison["naive"]],
        "feedback_aware": [
            asdict(item) for item in comparison["feedback_aware"]
        ],
        "changed_choice": comparison["changed_choice"],
    }


def _prospective_benchmark() -> dict[str, object]:
    event_at = datetime(2027, 1, 15, 12, 0, tzinfo=timezone.utc)
    created_at = event_at - timedelta(days=7)
    entry = create_prospective_entry(
        event_id="future-natural-experiment",
        event_at=event_at,
        created_at=created_at,
        model_name="frontier-demo",
        outcome_names=("y0", "y1"),
        prediction=(0.8, -0.4),
        metadata={
            "protocol": "sealed before event",
            "purpose": "prospective falsification",
        },
    )
    score = score_prospective_entry(
        entry,
        outcome=(0.7, -0.5),
        observed_at=event_at + timedelta(hours=1),
    )
    return {
        "seal": entry.seal,
        "seal_valid": entry.verify(),
        "score": asdict(score),
    }


def _objective_benchmark() -> dict[str, object]:
    objective = FalsifiableCausalCompressionObjective()
    compact_falsifiable = objective.score(
        ScientificObjectiveTerms(
            prediction_error=0.05,
            description_length=6.0,
            invariance_penalty=0.08,
            calibration_penalty=0.05,
            posterior_entropy=0.12,
            expected_information_gain=0.55,
            experiment_cost=0.08,
            performative_feedback=0.04,
            unknown_mass=0.04,
        )
    )
    brittle_fit = objective.score(
        ScientificObjectiveTerms(
            prediction_error=0.18,
            description_length=3.0,
            invariance_penalty=0.75,
            calibration_penalty=0.45,
            posterior_entropy=0.60,
            expected_information_gain=0.08,
            experiment_cost=0.04,
            performative_feedback=0.55,
            unknown_mass=0.70,
        )
    )
    return {
        "compact_falsifiable_score": compact_falsifiable.total,
        "brittle_fit_score": brittle_fit.total,
        "prefers_compact_falsifiable": (
            compact_falsifiable.total < brittle_fit.total
        ),
    }


def run_frontier_benchmark(seed: int = 7) -> dict[str, object]:
    domains: dict[str, dict[str, object]] = {}
    for offset, domain in enumerate(("physics", "ecology", "epidemic")):
        x, truth, interventions = _domain_problem(
            domain,
            seed=seed + offset * 1_003,
        )
        learner = InterventionAwareOntologyLearner(
            feature_count=64,
            bandwidth=1.5,
            ridge=0.05,
            permutations=8,
            seed=seed + offset * 1_003,
        )
        result = learner.fit(x, interventions)
        learned = result.transform(x)
        learned_r2 = _latent_recovery_score(learned, truth)

        pca_coords = PCA(
            n_components=2,
            random_state=seed,
        ).fit_transform(x)
        pca_r2 = _latent_recovery_score(pca_coords, truth)

        domains[domain] = {
            "selected_dim": result.selected_dim,
            "canonical_correlations": result.canonical_correlations.tolist(),
            "null_thresholds": result.null_thresholds.tolist(),
            "latent_recovery_r2": learned_r2,
            "pca_r2": pca_r2,
            "improvement_over_pca": learned_r2 - pca_r2,
        }

    natural_x, true_regimes = _natural_regime_problem(seed=seed + 77)
    natural = NaturalEnvironmentDiscoverer(
        window=24,
        max_regimes=6,
        seed=seed + 77,
    ).fit_transform(natural_x)
    natural_ari = float(adjusted_rand_score(true_regimes, natural.labels))

    latent_laws = LatentLawCompiler(
        max_terms=3,
        beam_width=32,
        top_k=12,
    ).fit(_henon_trajectory(seed=seed + 99))

    joint_x, _, joint_controls = _controlled_joint_problem(seed=seed + 101)
    joint = JointOntologyLawLearner(
        ontology_learner=InterventionAwareOntologyLearner(
            feature_count=48,
            bandwidth=1.5,
            ridge=0.05,
            permutations=6,
            seed=seed + 101,
        ),
        law_compiler=LatentLawCompiler(
            max_terms=4,
            beam_width=40,
            top_k=12,
        ),
        complexity_weight=0.01,
        intervention_weight=0.10,
    ).fit(joint_x, joint_controls)

    invention = _theory_invention_benchmark(seed + 123)
    evolution = _ontology_evolution_benchmark(seed + 211)
    performative = _performative_benchmark(seed + 307)
    prospective = _prospective_benchmark()
    objective = _objective_benchmark()

    improvements = [
        float(result["improvement_over_pca"])
        for result in domains.values()
    ]
    selected_dims = [
        int(result["selected_dim"])
        for result in domains.values()
    ]

    return {
        "version": "openmechanism-frontier-v1",
        "cross_domain_ontology": domains,
        "cross_domain_summary": {
            "mean_improvement_over_pca": float(np.mean(improvements)),
            "minimum_improvement_over_pca": float(np.min(improvements)),
            "selected_dims": selected_dims,
        },
        "natural_experiments": {
            "adjusted_rand_index": natural_ari,
            "cluster_count": natural.cluster_count,
            "silhouette": natural.silhouette,
        },
        "latent_laws": {
            "mean_validation_mse": latent_laws.mean_validation_mse,
            "mean_validation_r2": latent_laws.mean_validation_r2,
            "total_complexity": latent_laws.total_complexity,
            "laws": [asdict(item) for item in latent_laws.laws],
        },
        "joint_ontology_law": {
            "selected_dim": joint.selected_dim,
            "objective": joint.objective,
            "candidate_objectives": list(joint.candidate_objectives),
            "mean_validation_r2": joint.law_result.mean_validation_r2,
            "total_complexity": joint.law_result.total_complexity,
            "laws": [asdict(item) for item in joint.law_result.laws],
        },
        "theory_invention": invention,
        "ontology_evolution": evolution,
        "performative_selection": performative,
        "prospective_falsification": prospective,
        "unified_objective": objective,
        "scientific_boundary": (
            "This suite demonstrates cross-domain controlled mechanism-discovery "
            "capabilities. It does not establish discovery of previously unknown "
            "real-world scientific laws. That requires external prospective evidence."
        ),
    }
