from __future__ import annotations

from .breakthrough_bench import run_breakthrough_benchmark


class BreakthroughResearchEngine:
    """Runs the first falsifiable V3 causal-renormalization research suite."""

    def __init__(self, seed: int = 7) -> None:
        self.seed = int(seed)

    def run(self) -> dict[str, object]:
        report = run_breakthrough_benchmark(seed=self.seed)
        ontology = report["ontology"]
        experiment_design = report["experiment_design"]
        open_world = report["open_world"]

        checks = {
            "ontology_beats_pca": bool(
                ontology["causal_latent_recovery_r2"]
                > ontology["pca_latent_recovery_r2"]
            ),
            "diagnostic_probe_selected": bool(
                experiment_design
                and experiment_design[0]["name"] == "diagnostic_probe"
            ),
            "known_case_prefers_known": bool(
                open_world["familiar_observation"]["unknown_probability"] < 0.5
            ),
            "alien_case_prefers_unknown": bool(
                open_world["alien_observation"]["unknown_probability"] > 0.5
            ),
            "claim_seal_valid": bool(report["scientific_seal"]["valid"]),
        }
        return {
            "version": "v3-causal-renormalization-alpha",
            "checks": checks,
            "all_checks_pass": all(checks.values()),
            **report,
        }
