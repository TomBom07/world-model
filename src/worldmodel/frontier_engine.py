from __future__ import annotations

from .frontier_bench import run_frontier_benchmark


class FrontierResearchEngine:
    """Runs the V4 multi-domain falsification suite."""

    def __init__(self, seed: int = 7) -> None:
        self.seed = int(seed)

    def run(self) -> dict[str, object]:
        report = run_frontier_benchmark(seed=self.seed)

        summary = report["cross_domain_summary"]
        natural = report["natural_experiments"]
        laws = report["latent_laws"]
        joint = report["joint_ontology_law"]
        invention = report["theory_invention"]
        evolution = report["ontology_evolution"]
        performative = report["performative_selection"]
        prospective = report["prospective_falsification"]
        objective = report["unified_objective"]

        invented = invention["invented"]
        invented_terms = set(invented["terms"]) if invented else set()

        checks = {
            "nonlinear_ontology_beats_pca_in_every_domain": bool(
                summary["minimum_improvement_over_pca"] > 0.02
            ),
            "automatic_latent_dimension_is_two": bool(
                all(value == 2 for value in summary["selected_dims"])
            ),
            "natural_experiment_regimes_recovered": bool(
                natural["adjusted_rand_index"] > 0.80
            ),
            "latent_laws_are_predictive": bool(
                laws["mean_validation_r2"] > 0.90
            ),
            "joint_ontology_and_law_discovery_is_predictive": bool(
                joint["selected_dim"] == 2
                and joint["mean_validation_r2"] > 0.55
            ),
            "open_world_rejects_incomplete_family": bool(
                invention["open_world"]["unknown_probability"] > 0.50
            ),
            "new_symbolic_theory_improves_holdout": bool(
                invented
                and invented["accepted"]
                and invented["relative_improvement"] > 0.70
            ),
            "invented_theory_contains_missing_interaction": bool(
                "x0*x1" in invented_terms
            ),
            "ontology_split_detected": bool(
                evolution["splits"]
                and evolution["splits"][0]["dimension"] == 0
            ),
            "ontology_merge_detected": bool(
                any(
                    {item["left"], item["right"]} == {1, 2}
                    for item in evolution["merges"]
                )
            ),
            "performative_cost_changes_experiment_choice": bool(
                performative["changed_choice"]
                and performative["naive"][0]["name"] == "maximal_but_reflexive"
                and performative["feedback_aware"][0]["name"]
                == "slightly_weaker_low_feedback"
            ),
            "prospective_claim_is_sealed_and_scorable": bool(
                prospective["seal_valid"]
                and prospective["score"]["seal_valid"]
                and prospective["score"]["mae"] < 0.2
            ),
            "unified_objective_prefers_falsifiable_theory": bool(
                objective["prefers_compact_falsifiable"]
            ),
        }

        return {
            "version": "v4-frontier-suite",
            "seed": self.seed,
            "checks": checks,
            "all_checks_pass": all(checks.values()),
            **report,
        }
