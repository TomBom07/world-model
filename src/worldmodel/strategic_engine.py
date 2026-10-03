from __future__ import annotations

from dataclasses import asdict

import numpy as np

from .beliefs import compress_belief_field
from .evaluation import (
    active_identification_benchmark,
    belief_order_ablation,
    observational_equivalence,
)
from .identification import ActiveWorldIdentifier
from .strategic import MECHANISMS, StrategicMarketSimulator


class StrategicResearchEngine:
    """V1 experiment: infer which hidden strategic world is generating observations."""

    def __init__(self, seed: int = 7) -> None:
        self.seed = int(seed)

    def run_demo(self, n: int = 260) -> dict[str, object]:
        simulator = StrategicMarketSimulator(seed=self.seed)
        belief_world, liquidity_world = simulator.paired_worlds(n=n)

        prefix = min(120, n // 2)
        equivalence = observational_equivalence(
            belief_world,
            liquidity_world,
            prefix=prefix,
        )

        true_mechanism = MECHANISMS[self.seed % len(MECHANISMS)]
        true_world = (
            belief_world
            if true_mechanism == "belief_reflexive"
            else liquidity_world
        )

        event_index = min(n - 20, max(prefix + 12, int(n * 0.62)))
        identifier = ActiveWorldIdentifier(simulator, observation_sigma=0.08)
        ranked = identifier.rank_probes(true_world.events, event_index)
        identification = identifier.observe_ranked(
            ranked[0],
            true_mechanism=true_mechanism,
            observation_seed=self.seed + 30_001,
        )

        random_rng = np.random.default_rng(self.seed + 81_337)
        baseline_candidates = ranked[1:] if len(ranked) > 1 else ranked
        random_probe = baseline_candidates[
            int(random_rng.integers(0, len(baseline_candidates)))
        ]
        random_identification = identifier.observe_ranked(
            random_probe,
            true_mechanism=true_mechanism,
            observation_seed=self.seed + 40_001,
        )

        field = compress_belief_field(true_world, n_factors=4)
        ablations = [
            belief_order_ablation(belief_world),
            belief_order_ablation(liquidity_world),
        ]
        benchmark = active_identification_benchmark(
            trials=16,
            n=min(max(n, 180), 240),
            event_index=min(145, n - 24),
            observation_sigma=0.08,
        )

        path_points = min(prefix, 120)
        belief_path = belief_world.prices[:path_points, 0]
        liquidity_path = liquidity_world.prices[:path_points, 0]

        return {
            "experiment": {
                "seed": self.seed,
                "observations": n,
                "observational_prefix": prefix,
                "diagnostic_event_index": event_index,
                "true_mechanism": true_mechanism,
                "candidate_mechanisms": list(MECHANISMS),
                "important_note": (
                    "Diagnostic probes represent future events to wait for and pre-register, "
                    "not events to cause in a real market."
                ),
            },
            "observational_equivalence": asdict(equivalence),
            "path_preview": {
                "belief_reflexive": belief_path.tolist(),
                "liquidity_reflexive": liquidity_path.tolist(),
            },
            "active_identification": {
                "selected_probe": asdict(identification.selected_probe),
                "information_score": identification.information_score,
                "prior": identification.prior,
                "posterior": identification.posterior,
                "predicted_mechanism": identification.predicted_mechanism,
                "correct": identification.correct,
                "entropy_before": identification.entropy_before,
                "entropy_after": identification.entropy_after,
                "observation": identification.observation.tolist(),
                "fingerprints": {
                    key: value.tolist()
                    for key, value in identification.predicted_fingerprints.items()
                },
                "top_probes": [
                    {
                        "label": item.probe.label,
                        "event_kind": item.probe.event_kind,
                        "magnitude": item.probe.magnitude,
                        "information_score": item.information_score,
                    }
                    for item in ranked[:6]
                ],
            },
            "random_identification": {
                "selected_probe": asdict(random_identification.selected_probe),
                "posterior": random_identification.posterior,
                "predicted_mechanism": random_identification.predicted_mechanism,
                "correct": random_identification.correct,
                "entropy_before": random_identification.entropy_before,
                "entropy_after": random_identification.entropy_after,
            },
            "belief_field": {
                "factors": field.summary(top_k=4),
                "mean_disagreement": float(field.disagreement.mean()),
                "mean_higher_order_gap": float(np.mean(np.abs(field.higher_order_gap))),
            },
            "belief_ablation": [asdict(item) for item in ablations],
            "hidden_mechanics": {
                "belief_reflexive": {
                    "mean_leverage": float(belief_world.leverage[:, 4].mean()),
                    "dealer_hedge_magnitude": float(np.mean(np.abs(belief_world.dealer_hedge))),
                    "margin_calls": belief_world.margin_call_count,
                },
                "liquidity_reflexive": {
                    "mean_leverage": float(liquidity_world.leverage[:, 4].mean()),
                    "dealer_hedge_magnitude": float(np.mean(np.abs(liquidity_world.dealer_hedge))),
                    "margin_calls": liquidity_world.margin_call_count,
                },
            },
            "identification_benchmark": asdict(benchmark),
            "scientific_boundary": (
                "V1 proves only that active identification can distinguish known synthetic "
                "mechanisms in this controlled simulator. It does not establish causal "
                "identification or trading edge in real markets."
            ),
        }
