from __future__ import annotations

from datetime import timedelta

from .historical_runner import SealedHistoricalRunner
from .sealing import ExperimentSpec
from .synthetic_history import generate_synthetic_history


class HistoricalResearchEngine:
    """Phase-2 protocol demonstration using historical-shaped synthetic events."""

    def __init__(self, seed: int = 7) -> None:
        self.seed = int(seed)

    def run_demo(self, n: int = 120) -> dict[str, object]:
        dataset = generate_synthetic_history(seed=self.seed, n=n)
        split_index = max(24, int(n * 0.68))
        evaluation_start_index = split_index + 1
        if evaluation_start_index >= n:
            raise ValueError("Not enough rows for a sealed evaluation period")

        training_end = dataset.records[split_index].event_at
        evaluation_start = dataset.records[evaluation_start_index].event_at
        evaluation_end = dataset.records[-1].event_at

        spec = ExperimentSpec(
            name="phase2-protocol-demo",
            training_end=training_end,
            evaluation_start=evaluation_start,
            evaluation_end=evaluation_end,
            event_families=(),
            feature_names=dataset.feature_names,
            outcome_names=dataset.outcome_names,
            model_config={
                "freeze_at_training_end": True,
                "interval": "80%",
                "evaluation": "chronological",
                "outcome_window": "synthetic event reaction",
            },
        )
        report = SealedHistoricalRunner(
            dataset,
            spec,
            seed=self.seed,
            code_ref="rmc-v2-sealed-history",
        ).run()

        report["experiment"] = {
            "seed": self.seed,
            "observations": n,
            "training_end": training_end,
            "evaluation_start": evaluation_start,
            "evaluation_end": evaluation_end,
            "frozen_days_before_eval": (
                evaluation_start - training_end
            ).total_seconds()
            / 86400,
        }
        return report
