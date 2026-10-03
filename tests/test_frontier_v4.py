from datetime import datetime, timedelta, timezone

import pytest

from worldmodel.frontier_engine import FrontierResearchEngine
from worldmodel.frontier_bench import run_frontier_benchmark
from worldmodel.prospective import create_prospective_entry, score_prospective_entry


def test_frontier_suite_passes_default_seed():
    report = FrontierResearchEngine(seed=7).run()
    assert report["all_checks_pass"], report


def test_cross_domain_nonlinear_ontology_is_not_single_domain_luck():
    report = run_frontier_benchmark(seed=11)
    domains = report["cross_domain_ontology"]
    assert set(domains) == {"physics", "ecology", "epidemic"}
    assert all(item["selected_dim"] == 2 for item in domains.values())
    assert all(item["improvement_over_pca"] > 0 for item in domains.values())


def test_frontier_invents_missing_mechanism_family():
    report = run_frontier_benchmark(seed=5)
    invention = report["theory_invention"]
    assert invention["open_world"]["unknown_probability"] > 0.5
    assert invention["invented"] is not None
    assert invention["invented"]["accepted"]
    assert "x0*x1" in invention["invented"]["terms"]


def test_prospective_registry_enforces_time_arrow():
    event_at = datetime(2027, 2, 1, tzinfo=timezone.utc)
    entry = create_prospective_entry(
        event_id="future-test",
        event_at=event_at,
        created_at=event_at - timedelta(days=1),
        model_name="test",
        outcome_names=("y",),
        prediction=(1.0,),
    )
    assert entry.verify()

    with pytest.raises(ValueError, match="before the event"):
        score_prospective_entry(
            entry,
            outcome=(1.0,),
            observed_at=event_at - timedelta(seconds=1),
        )


def test_frontier_detects_split_and_merge_ontology_pressure():
    report = run_frontier_benchmark(seed=13)
    evolution = report["ontology_evolution"]
    assert evolution["splits"][0]["dimension"] == 0
    assert any(
        {item["left"], item["right"]} == {1, 2}
        for item in evolution["merges"]
    )
