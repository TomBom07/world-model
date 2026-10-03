from __future__ import annotations

from dataclasses import asdict

import numpy as np
from sklearn.metrics import mean_absolute_error

from .adversary import stress_test
from .benchmarks import sample_efficiency_benchmark
from .compiler import MechanismCompiler
from .invariants import prediction_invariant
from .ontology import suggest_missing_mechanisms
from .regimes import ResidualRegimeDetector
from .simulator import ReflexiveMarketSimulator
from .tomography import belief_tomography


class ResearchEngine:
    """Orchestrates the falsifiable RMC research loop."""

    def __init__(self, seed: int = 7) -> None:
        self.seed = seed

    @staticmethod
    def _overlap(recovered: tuple[str, ...], truth: tuple[str, ...]) -> float:
        a, b = set(recovered), set(truth)
        return float(len(a & b) / len(a | b)) if (a | b) else 1.0

    def run_demo(self, n: int = 360, target: str = "growth_equity") -> dict[str, object]:
        simulator = ReflexiveMarketSimulator(seed=self.seed)
        world = simulator.generate(n=n, switch_at=0.58)
        y = world.target(target)
        switch = world.switch_index

        pre_train_end = max(48, int(switch * 0.72))
        compiler = MechanismCompiler(max_terms=5, beam_width=48, top_k=16)
        pre = compiler.fit(world.x[:pre_train_end], y[:pre_train_end], world.feature_names)
        pre_pred = pre.best.predict(world.x)
        pre_mae = float(mean_absolute_error(y[pre_train_end:switch], pre_pred[pre_train_end:switch]))

        residuals = y - pre_pred
        detector = ResidualRegimeDetector(window=max(16, n // 18), threshold=2.1)
        search_start = max(0, pre_train_end - detector.window)
        detected = detector.detect(residuals[search_start:])
        detected_index = detected.index + search_start if detected.index is not None else None

        post_start = min(n - 80, switch + 8)
        post_test_start = max(post_start + 48, n - 56)
        post_test_start = min(post_test_start, n - 24)
        post = compiler.fit(world.x[post_start:post_test_start], y[post_start:post_test_start], world.feature_names)
        post_pred = post.best.predict(world.x[post_test_start:])
        post_mae = float(mean_absolute_error(y[post_test_start:], post_pred))

        truth_pre = world.hidden_terms[0][target]
        truth_post = world.hidden_terms[1][target]

        tomo = belief_tomography(world.y, world.target_names, n_factors=3)

        post_residuals_from_old_world = residuals[switch:]
        ontology = suggest_missing_mechanisms(
            world.x[switch:],
            post_residuals_from_old_world,
            world.feature_names,
            used_terms=set(pre.best.term_names),
            top_k=6,
        )

        latest_x = world.x[-1]
        invariant = prediction_invariant(post, latest_x)
        adversarial = stress_test(
            post,
            latest_x,
            world.feature_names,
            feature_scales=world.x[post_start:post_test_start].std(axis=0),
            magnitude=1.0,
            top_k=6,
        )

        model_table = [
            {
                "rank": i + 1,
                "program": model.as_program(),
                "mdl_score": model.score,
                "mse": model.mse,
                "posterior": model.posterior,
                "terms": list(model.term_names),
            }
            for i, model in enumerate(post.models[:8])
        ]

        return {
            "experiment": {
                "seed": self.seed,
                "observations": n,
                "target": target,
                "true_switch_index": switch,
                "detected_switch_index": detected_index,
                "break_score": detected.score,
            },
            "pre_regime": {
                "truth_terms": list(truth_pre),
                "recovered_terms": list(pre.best.term_names),
                "program": pre.best.as_program(),
                "term_recovery_jaccard": self._overlap(pre.best.term_names, truth_pre),
                "mae": pre_mae,
            },
            "post_regime": {
                "truth_terms": list(truth_post),
                "recovered_terms": list(post.best.term_names),
                "program": post.best.as_program(),
                "term_recovery_jaccard": self._overlap(post.best.term_names, truth_post),
                "mae": post_mae,
                "top_models": model_table,
            },
            "tomography": tomo.summary(),
            "ontology_break": [asdict(item) for item in ontology],
            "prediction_invariant": asdict(invariant),
            "adversarial_scenarios": [asdict(item) for item in adversarial],
            "sample_efficiency": sample_efficiency_benchmark(seed=self.seed + 100),
            "disclaimer": (
                "Synthetic research environment only. This experiment tests mechanism recovery; "
                "it is not evidence of real-market predictive edge or investment performance."
            ),
        }
