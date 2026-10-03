from __future__ import annotations

from dataclasses import dataclass
from math import log

import numpy as np

from .strategic import EVENTS, MECHANISMS, StrategicMarketSimulator, StrategicWorld


@dataclass(frozen=True)
class Probe:
    event_kind: str
    magnitude: float
    horizon: int = 3

    @property
    def label(self) -> str:
        sign = "+" if self.magnitude >= 0 else ""
        return f"{self.event_kind} {sign}{self.magnitude:.1f}σ"


@dataclass(frozen=True)
class RankedProbe:
    probe: Probe
    information_score: float
    fingerprints: dict[str, np.ndarray]


@dataclass(frozen=True)
class IdentificationResult:
    prior: dict[str, float]
    posterior: dict[str, float]
    selected_probe: Probe
    information_score: float
    observation: np.ndarray
    predicted_fingerprints: dict[str, np.ndarray]
    predicted_mechanism: str
    true_mechanism: str | None
    correct: bool | None
    entropy_before: float
    entropy_after: float


def _entropy(weights: dict[str, float]) -> float:
    values = np.asarray(list(weights.values()), dtype=float)
    values = values[values > 0]
    return float(-np.sum(values * np.log(values)))


class ActiveWorldIdentifier:
    """Choose the future event whose reaction best separates hidden-world hypotheses.

    In a real market this means waiting for or pre-registering a naturally occurring
    diagnostic event, not causing one. Each candidate mechanism predicts a cross-asset
    reaction fingerprint before the event, then Bayes-style weights are updated after
    the event occurs.
    """

    def __init__(
        self,
        simulator: StrategicMarketSimulator,
        *,
        mechanisms: tuple[str, ...] = MECHANISMS,
        observation_sigma: float = 0.08,
    ) -> None:
        self.simulator = simulator
        self.mechanisms = tuple(mechanisms)
        self.observation_sigma = float(observation_sigma)

    @staticmethod
    def default_probes(magnitude: float = 2.0, horizon: int = 3) -> tuple[Probe, ...]:
        return tuple(
            Probe(event, direction * abs(magnitude), horizon)
            for event in EVENTS
            for direction in (-1.0, 1.0)
        )

    def _fingerprints(
        self,
        events: np.ndarray,
        event_index: int,
        probe: Probe,
        baselines: dict[str, StrategicWorld] | None = None,
    ) -> dict[str, np.ndarray]:
        baselines = baselines or {
            mechanism: self.simulator.simulate(mechanism, events=events)
            for mechanism in self.mechanisms
        }
        end = min(len(events), event_index + max(1, int(probe.horizon)))
        fingerprints: dict[str, np.ndarray] = {}

        for mechanism in self.mechanisms:
            shocked = self.simulator.simulate(
                mechanism,
                events=events,
                diagnostic=(event_index, probe.event_kind, probe.magnitude),
            )
            fingerprints[mechanism] = (
                shocked.returns[event_index:end]
                - baselines[mechanism].returns[event_index:end]
            ).sum(axis=0)
        return fingerprints

    def rank_probes(
        self,
        events: np.ndarray,
        event_index: int,
        probes: tuple[Probe, ...] | None = None,
    ) -> list[RankedProbe]:
        probes = probes or self.default_probes()
        baselines = {
            mechanism: self.simulator.simulate(mechanism, events=events)
            for mechanism in self.mechanisms
        }
        ranked: list[RankedProbe] = []

        for probe in probes:
            fingerprints = self._fingerprints(events, event_index, probe, baselines)
            values = list(fingerprints.values())
            pairwise: list[float] = []
            for i in range(len(values)):
                for j in range(i + 1, len(values)):
                    pairwise.append(
                        float(
                            np.linalg.norm(values[i] - values[j])
                            / max(self.observation_sigma, 1e-9)
                        )
                    )
            score = float(np.mean(pairwise)) if pairwise else 0.0
            ranked.append(RankedProbe(probe, score, fingerprints))

        ranked.sort(key=lambda item: item.information_score, reverse=True)
        return ranked

    def update(
        self,
        *,
        prior: dict[str, float],
        observation: np.ndarray,
        fingerprints: dict[str, np.ndarray],
    ) -> dict[str, float]:
        observation = np.asarray(observation, dtype=float)
        sigma = max(self.observation_sigma, 1e-9)
        log_weights: dict[str, float] = {}

        for mechanism in self.mechanisms:
            predicted = np.asarray(fingerprints[mechanism], dtype=float)
            error = observation - predicted
            log_likelihood = -0.5 * float(np.sum((error / sigma) ** 2))
            log_weights[mechanism] = log(max(prior.get(mechanism, 0.0), 1e-12)) + log_likelihood

        maximum = max(log_weights.values())
        raw = {key: np.exp(value - maximum) for key, value in log_weights.items()}
        normalizer = float(sum(raw.values()))
        return {key: float(value / normalizer) for key, value in raw.items()}

    def observe_ranked(
        self,
        ranked_probe: RankedProbe,
        *,
        true_mechanism: str,
        prior: dict[str, float] | None = None,
        observation_seed: int | None = None,
    ) -> IdentificationResult:
        if true_mechanism not in self.mechanisms:
            raise ValueError(f"true_mechanism must be one of {self.mechanisms}")

        if prior is None:
            prior = {mechanism: 1.0 / len(self.mechanisms) for mechanism in self.mechanisms}
        else:
            total = float(sum(prior.get(mechanism, 0.0) for mechanism in self.mechanisms))
            if total <= 0:
                raise ValueError("prior must contain positive mass")
            prior = {
                mechanism: float(prior.get(mechanism, 0.0) / total)
                for mechanism in self.mechanisms
            }

        truth = ranked_probe.fingerprints[true_mechanism]
        seed = self.simulator.seed + 12_345 if observation_seed is None else observation_seed
        rng = np.random.default_rng(seed)
        observation = truth + rng.normal(0, self.observation_sigma, size=len(truth))
        posterior = self.update(
            prior=prior,
            observation=observation,
            fingerprints=ranked_probe.fingerprints,
        )
        predicted = max(posterior, key=posterior.get)

        return IdentificationResult(
            prior=dict(prior),
            posterior=posterior,
            selected_probe=ranked_probe.probe,
            information_score=ranked_probe.information_score,
            observation=observation,
            predicted_fingerprints=ranked_probe.fingerprints,
            predicted_mechanism=predicted,
            true_mechanism=true_mechanism,
            correct=predicted == true_mechanism,
            entropy_before=_entropy(prior),
            entropy_after=_entropy(posterior),
        )

    def identify(
        self,
        *,
        events: np.ndarray,
        event_index: int,
        true_mechanism: str,
        probe: Probe | None = None,
        prior: dict[str, float] | None = None,
        observation_seed: int | None = None,
    ) -> IdentificationResult:
        if probe is None:
            ranked_probe = self.rank_probes(events, event_index)[0]
        else:
            fingerprints = self._fingerprints(events, event_index, probe)
            values = list(fingerprints.values())
            pairwise: list[float] = []
            for i in range(len(values)):
                for j in range(i + 1, len(values)):
                    pairwise.append(
                        float(
                            np.linalg.norm(values[i] - values[j])
                            / max(self.observation_sigma, 1e-9)
                        )
                    )
            ranked_probe = RankedProbe(
                probe=probe,
                information_score=float(np.mean(pairwise)) if pairwise else 0.0,
                fingerprints=fingerprints,
            )
        return self.observe_ranked(
            ranked_probe,
            true_mechanism=true_mechanism,
            prior=prior,
            observation_seed=observation_seed,
        )
