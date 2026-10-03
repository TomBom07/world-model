from __future__ import annotations

from worldmodel.frontier_engine import FrontierResearchEngine


def test_frontier_v4_canonical_suite_passes() -> None:
    result = FrontierResearchEngine(seed=7).run()

    assert result["version"] == "v4-frontier-suite"
    assert result["all_checks_pass"], [name for name, ok in result["checks"].items() if not ok]
    assert all(result["checks"].values())
    assert result["cross_domain_summary"]["minimum_improvement_over_pca"] > 0.02
    assert result["natural_experiments"]["adjusted_rand_index"] > 0.80
    assert result["latent_laws"]["mean_validation_r2"] > 0.90
    assert result["joint_ontology_law"]["selected_dim"] == 2

    invented = result["theory_invention"]["invented"]
    assert invented is not None
    assert invented["accepted"]
    assert "x0*x1" in invented["terms"]
    assert result["prospective_falsification"]["seal_valid"]
