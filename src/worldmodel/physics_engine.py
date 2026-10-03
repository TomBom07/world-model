from __future__ import annotations

from dataclasses import asdict

import numpy as np

from .experiment_design import (
    ExperimentCandidate,
    ExpectedInformationGainSelector,
    entropy,
    gaussian_posterior,
)
from .physics import MECHANISMS, HiddenPhysicsSimulator, PhysicsProbe


class PhysicsDiscoveryEngine:
    """Cross-domain proof that active world identification is not market-specific."""

    def __init__(self, seed: int = 7, *, observation_sigma: float = 0.12) -> None:
        self.seed = int(seed)
        self.observation_sigma = float(observation_sigma)

    def _candidates(
        self,
        simulator: HiddenPhysicsSimulator,
        forces: np.ndarray,
        event_index: int,
    ) -> tuple[list[ExperimentCandidate], dict[str, PhysicsProbe]]:
        candidates: list[ExperimentCandidate] = []
        probes: dict[str, PhysicsProbe] = {}
        for probe in simulator.default_probes():
            predictions = {
                mechanism: simulator.fingerprint(
                    mechanism,
                    forces=forces,
                    event_index=event_index,
                    probe=probe,
                )
                for mechanism in MECHANISMS
            }
            candidates.append(
                ExperimentCandidate(
                    name=probe.name,
                    predictions=predictions,
                    cost=abs(probe.force) * probe.duration,
                )
            )
            probes[probe.name] = probe
        return candidates, probes

    def _observe(
        self,
        candidate: ExperimentCandidate,
        *,
        true_mechanism: str,
        noise_seed: int,
    ) -> tuple[np.ndarray, dict[str, float]]:
        rng = np.random.default_rng(noise_seed)
        truth = np.asarray(candidate.predictions[true_mechanism], dtype=float)
        observation = truth + rng.normal(
            0.0,
            self.observation_sigma,
            size=len(truth),
        )
        prior = {mechanism: 1.0 / len(MECHANISMS) for mechanism in MECHANISMS}
        posterior = gaussian_posterior(
            prior,
            observation,
            candidate.predictions,
            self.observation_sigma,
        )
        return observation, posterior

    def benchmark(self, trials: int = 16, n: int = 220) -> dict[str, float | int]:
        active_true_mass: list[float] = []
        random_true_mass: list[float] = []
        active_entropy_drop: list[float] = []
        random_entropy_drop: list[float] = []
        active_correct = 0
        random_correct = 0
        prior = {mechanism: 1.0 / len(MECHANISMS) for mechanism in MECHANISMS}
        h0 = entropy(prior)

        for offset in range(trials):
            seed = self.seed + 1000 + offset
            simulator = HiddenPhysicsSimulator(seed=seed)
            forces = simulator.generate_forces(n)
            event_index = min(n - 40, max(130, int(n * 0.66)))
            candidates, _ = self._candidates(simulator, forces, event_index)
            ranked = ExpectedInformationGainSelector(
                sigma=self.observation_sigma,
                samples_per_hypothesis=64,
                seed=seed + 21,
            ).score(candidates, prior)
            by_name = {candidate.name: candidate for candidate in candidates}
            active = by_name[ranked[0].name]

            rng = np.random.default_rng(seed + 37)
            random_candidate = candidates[int(rng.integers(0, len(candidates)))]
            true_mechanism = MECHANISMS[seed % len(MECHANISMS)]

            _, active_post = self._observe(
                active,
                true_mechanism=true_mechanism,
                noise_seed=seed + 51,
            )
            _, random_post = self._observe(
                random_candidate,
                true_mechanism=true_mechanism,
                noise_seed=seed + 51,
            )

            active_true_mass.append(active_post[true_mechanism])
            random_true_mass.append(random_post[true_mechanism])
            active_entropy_drop.append(h0 - entropy(active_post))
            random_entropy_drop.append(h0 - entropy(random_post))
            active_correct += max(active_post, key=active_post.get) == true_mechanism
            random_correct += max(random_post, key=random_post.get) == true_mechanism

        return {
            "trials": trials,
            "active_accuracy": active_correct / trials,
            "random_accuracy": random_correct / trials,
            "active_true_posterior": float(np.mean(active_true_mass)),
            "random_true_posterior": float(np.mean(random_true_mass)),
            "active_entropy_reduction": float(np.mean(active_entropy_drop)),
            "random_entropy_reduction": float(np.mean(random_entropy_drop)),
        }

    def run_demo(self, n: int = 240) -> dict[str, object]:
        if n < 180:
            raise ValueError("n must be at least 180")

        simulator = HiddenPhysicsSimulator(seed=self.seed)
        forces = simulator.generate_forces(n)
        linear, curved = simulator.paired_passive_worlds(n=n)
        prefix = min(120, n // 2)
        event_index = min(n - 40, max(prefix + 20, int(n * 0.66)))

        candidates, probes = self._candidates(simulator, forces, event_index)
        prior = {mechanism: 1.0 / len(MECHANISMS) for mechanism in MECHANISMS}
        ranked = ExpectedInformationGainSelector(
            sigma=self.observation_sigma,
            samples_per_hypothesis=160,
            seed=self.seed + 19,
        ).score(candidates, prior)
        by_name = {candidate.name: candidate for candidate in candidates}
        selected_score = ranked[0]
        selected = by_name[selected_score.name]
        selected_probe = probes[selected.name]

        true_mechanism = MECHANISMS[self.seed % len(MECHANISMS)]
        observation, posterior = self._observe(
            selected,
            true_mechanism=true_mechanism,
            noise_seed=self.seed + 30_011,
        )
        predicted_mechanism = max(posterior, key=posterior.get)

        equivalence = simulator.passive_equivalence(n=n, prefix=prefix)
        h_before = entropy(prior)
        h_after = entropy(posterior)

        return {
            "experiment": {
                "domain": "controlled_physics",
                "seed": self.seed,
                "observations": n,
                "passive_prefix": prefix,
                "probe_index": event_index,
                "true_mechanism": true_mechanism,
                "candidate_mechanisms": list(MECHANISMS),
            },
            "passive_equivalence": equivalence,
            "path_preview": {
                "linear_resistance": linear.velocity[1 : prefix + 1].tolist(),
                "curved_resistance": curved.velocity[1 : prefix + 1].tolist(),
            },
            "mechanisms": {
                "linear_resistance": {
                    "equation": "D(v) = k·v",
                    "k": simulator.linear_k,
                },
                "curved_resistance": {
                    "equation": "D(v) = c + q·v|v|",
                    "c": simulator.constant_load,
                    "q": simulator.curved_q,
                },
                "tangent_at_velocity": simulator.reference_velocity,
                "construction": (
                    "The two resistance laws have the same value and first derivative "
                    "at the reference velocity, making passive operation locally "
                    "indistinguishable to first order."
                ),
            },
            "active_identification": {
                "selected_probe": asdict(selected_probe),
                "expected_information_gain": selected_score.expected_information_gain,
                "prior": prior,
                "posterior": posterior,
                "predicted_mechanism": predicted_mechanism,
                "correct": predicted_mechanism == true_mechanism,
                "entropy_before": h_before,
                "entropy_after": h_after,
                "observation": observation.tolist(),
                "fingerprints": {
                    name: values.tolist()
                    for name, values in selected.predictions.items()
                },
                "ranked_probes": [
                    {
                        **asdict(probes[item.name]),
                        "expected_information_gain": item.expected_information_gain,
                        "expected_entropy_after": item.expected_entropy_after,
                    }
                    for item in ranked
                ],
            },
            "identification_benchmark": self.benchmark(
                trials=16,
                n=min(max(n, 200), 240),
            ),
            "scientific_boundary": (
                "This is a controlled synthetic system-identification test. The two "
                "candidate laws were intentionally constructed to be locally tangent. "
                "Success shows that active experiment selection can transfer beyond the "
                "market simulator; it does not establish autonomous discovery of unknown "
                "physical laws from unrestricted real-world data."
            ),
        }
