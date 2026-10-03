from datetime import datetime, timezone

import numpy as np

from worldmodel.breakthrough_bench import (
    generate_hidden_ontology_problem,
    run_breakthrough_benchmark,
)
from worldmodel.breakthrough_engine import BreakthroughResearchEngine
from worldmodel.experiment_design import (
    ExperimentCandidate,
    ExpectedInformationGainSelector,
)
from worldmodel.ontology_learning import CausalOntologyLearner
from worldmodel.open_world import OpenWorldBayes, UNKNOWN
from worldmodel.scientific_sealing import seal_scientific_claim


def test_causal_ontology_finds_intervention_relevant_coordinates():
    x, truth, environments = generate_hidden_ontology_problem(
        seed=21,
        samples_per_environment=140,
    )
    learner = CausalOntologyLearner(n_components=2, ridge=5e-3)
    z = learner.fit_transform(x, environments)

    assert z.shape == (len(x), 2)
    assert learner.result_ is not None
    assert learner.result_.separation_score > 0
    assert np.all(np.isfinite(learner.result_.eigenvalues))


def test_expected_information_gain_prefers_discriminating_probe():
    candidates = [
        ExperimentCandidate(
            "ambiguous",
            {"a": np.array([0.0]), "b": np.array([0.02])},
        ),
        ExperimentCandidate(
            "diagnostic",
            {"a": np.array([-1.0]), "b": np.array([1.0])},
        ),
    ]
    ranked = ExpectedInformationGainSelector(
        sigma=0.1,
        samples_per_hypothesis=96,
        seed=2,
    ).score(candidates, {"a": 0.5, "b": 0.5})

    assert ranked[0].name == "diagnostic"
    assert ranked[0].expected_information_gain > ranked[1].expected_information_gain


def test_open_world_can_say_none_of_the_above():
    model = OpenWorldBayes(sigma=0.1, unknown_scale=10.0, unknown_prior=0.1)
    predictions = {"a": np.array([0.0, 0.0]), "b": np.array([1.0, -1.0])}

    familiar = model.update(
        prior={"a": 0.5, "b": 0.5},
        observation=np.array([1.02, -0.98]),
        predictions=predictions,
    )
    alien = model.update(
        prior={"a": 0.5, "b": 0.5},
        observation=np.array([5.0, 5.0]),
        predictions=predictions,
    )

    assert familiar.posterior[UNKNOWN] < 0.5
    assert alien.posterior[UNKNOWN] > 0.5


def test_scientific_claim_seal_detects_tampering():
    now = datetime(2026, 10, 3, tzinfo=timezone.utc)
    claim = seal_scientific_claim(
        experiment_name="test",
        code_ref="abc123",
        data_cutoff=now,
        created_at=now,
        ontology={"latent_dim": 2},
        hypotheses={"a": "mechanism a"},
        posterior={"a": 1.0},
        selected_query={"name": "probe"},
        preregistered_predictions={"probe": [1.0]},
        evaluation_protocol={"metric": "mae"},
    )
    assert claim.verify()

    object.__setattr__(claim, "seal", "0" * 64)
    assert not claim.verify()


def test_v3_breakthrough_suite_smoke():
    report = run_breakthrough_benchmark(seed=7)

    assert report["scientific_seal"]["valid"] is True
    assert report["experiment_design"][0]["name"] == "diagnostic_probe"
    assert (
        report["open_world"]["alien_observation"]["unknown_probability"]
        > report["open_world"]["familiar_observation"]["unknown_probability"]
    )


def test_v3_full_research_checks_pass():
    report = BreakthroughResearchEngine(seed=7).run()
    assert report["all_checks_pass"], report
