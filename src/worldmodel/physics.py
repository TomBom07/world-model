from __future__ import annotations

from dataclasses import dataclass

import numpy as np


MECHANISMS = ("linear_resistance", "curved_resistance")


@dataclass(frozen=True)
class PhysicsProbe:
    name: str
    force: float
    duration: int
    horizon: int = 32


@dataclass(frozen=True)
class PhysicsTrace:
    mechanism: str
    forces: np.ndarray
    position: np.ndarray
    velocity: np.ndarray


class HiddenPhysicsSimulator:
    """A controlled system with locally indistinguishable resistance laws.

    The two resistance curves are constructed to have the same value and first
    derivative at the reference velocity. Around ordinary operation they therefore
    agree to first order; a sufficiently informative intervention reveals curvature.
    """

    def __init__(
        self,
        seed: int = 7,
        *,
        dt: float = 0.08,
        reference_velocity: float = 1.45,
        linear_k: float = 0.55,
    ) -> None:
        self.seed = int(seed)
        self.dt = float(dt)
        self.reference_velocity = float(reference_velocity)
        self.linear_k = float(linear_k)

        # D_linear(v) = k v
        # D_curved(v) = c + q v|v|
        # Choose c,q so value and slope match at reference_velocity.
        self.curved_q = self.linear_k / (2.0 * self.reference_velocity)
        self.constant_load = self.linear_k * self.reference_velocity / 2.0

    def generate_forces(self, n: int) -> np.ndarray:
        if n < 96:
            raise ValueError("n must be at least 96")
        rng = np.random.default_rng(self.seed + 11)
        t = np.arange(n, dtype=float)
        equilibrium = self.linear_k * self.reference_velocity
        return (
            equilibrium
            + 0.06 * np.sin(t / 9.0)
            + 0.04 * np.sin(t / 23.0)
            + rng.normal(0.0, 0.015, size=n)
        )

    def resistance(self, mechanism: str, velocity: float) -> float:
        if mechanism == "linear_resistance":
            return self.linear_k * velocity
        if mechanism == "curved_resistance":
            return self.constant_load + self.curved_q * velocity * abs(velocity)
        raise ValueError(f"unknown mechanism: {mechanism}")

    def simulate(
        self,
        mechanism: str,
        *,
        forces: np.ndarray,
        initial_position: float = 0.0,
        initial_velocity: float | None = None,
    ) -> PhysicsTrace:
        forces = np.asarray(forces, dtype=float)
        position = np.zeros(len(forces) + 1, dtype=float)
        velocity = np.zeros(len(forces) + 1, dtype=float)
        position[0] = float(initial_position)
        velocity[0] = (
            self.reference_velocity
            if initial_velocity is None
            else float(initial_velocity)
        )

        for t, force in enumerate(forces):
            acceleration = force - self.resistance(mechanism, velocity[t])
            velocity[t + 1] = velocity[t] + self.dt * acceleration
            position[t + 1] = position[t] + self.dt * velocity[t]

        return PhysicsTrace(
            mechanism=mechanism,
            forces=forces.copy(),
            position=position,
            velocity=velocity,
        )

    def paired_passive_worlds(self, n: int = 240) -> tuple[PhysicsTrace, PhysicsTrace]:
        forces = self.generate_forces(n)
        return (
            self.simulate("linear_resistance", forces=forces),
            self.simulate("curved_resistance", forces=forces),
        )

    @staticmethod
    def default_probes() -> tuple[PhysicsProbe, ...]:
        return (
            PhysicsProbe("tap", force=0.15, duration=4),
            PhysicsProbe("nudge", force=0.35, duration=5),
            PhysicsProbe("push", force=0.70, duration=6),
            PhysicsProbe("pulse", force=1.10, duration=8),
            PhysicsProbe("stress", force=1.70, duration=9),
        )

    def fingerprint(
        self,
        mechanism: str,
        *,
        forces: np.ndarray,
        event_index: int,
        probe: PhysicsProbe,
    ) -> np.ndarray:
        """Counterfactual response to a preregistered force pulse.

        The fingerprint is the probe-induced change in velocity and position relative
        to that same model's no-probe future. This prevents ordinary baseline drift
        from masquerading as diagnostic information.
        """
        forces = np.asarray(forces, dtype=float)
        if not 0 < event_index < len(forces):
            raise ValueError("event_index must lie inside force history")

        horizon = min(int(probe.horizon), len(forces) - event_index)
        if horizon < 8:
            raise ValueError("not enough future observations for probe")

        history = self.simulate(mechanism, forces=forces[:event_index])
        x0 = float(history.position[-1])
        v0 = float(history.velocity[-1])
        future = forces[event_index : event_index + horizon].copy()

        baseline = self.simulate(
            mechanism,
            forces=future,
            initial_position=x0,
            initial_velocity=v0,
        )

        shocked_forces = future.copy()
        shocked_forces[: min(probe.duration, horizon)] += probe.force
        shocked = self.simulate(
            mechanism,
            forces=shocked_forces,
            initial_position=x0,
            initial_velocity=v0,
        )

        sample_index = np.unique(np.linspace(1, horizon, 8, dtype=int))
        delta_velocity = shocked.velocity[sample_index] - baseline.velocity[sample_index]
        delta_position = shocked.position[sample_index] - baseline.position[sample_index]
        return np.concatenate([delta_velocity, delta_position])

    def passive_equivalence(self, n: int = 240, prefix: int = 120) -> dict[str, float]:
        linear, curved = self.paired_passive_worlds(n=n)
        prefix = min(prefix, n)
        a = linear.velocity[1 : prefix + 1]
        b = curved.velocity[1 : prefix + 1]
        combined_range = max(float(np.ptp(np.concatenate([a, b]))), 1e-9)
        return {
            "velocity_correlation": float(np.corrcoef(a, b)[0, 1]),
            "velocity_mae": float(np.mean(np.abs(a - b))),
            "velocity_normalized_mae": float(np.mean(np.abs(a - b)) / combined_range),
        }
