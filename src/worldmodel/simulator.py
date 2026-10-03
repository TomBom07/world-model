from __future__ import annotations

from dataclasses import dataclass

import numpy as np


FEATURES = (
    "growth_surprise",
    "inflation_surprise",
    "liquidity_shock",
    "crowding",
    "policy_surprise",
)

ASSETS = (
    "growth_equity",
    "value_equity",
    "two_year_yield",
    "usd",
    "gold",
    "volatility",
)


@dataclass(frozen=True)
class SyntheticWorld:
    x: np.ndarray
    y: np.ndarray
    feature_names: tuple[str, ...]
    target_names: tuple[str, ...]
    regimes: np.ndarray
    switch_index: int
    hidden_terms: dict[int, dict[str, tuple[str, ...]]]

    def target(self, name: str) -> np.ndarray:
        return self.y[:, self.target_names.index(name)]


class ReflexiveMarketSimulator:
    """Synthetic market with an explicit hidden regime change.

    The simulator is intentionally small enough that the true data-generating
    mechanisms are known. That gives us a falsifiable sandbox for testing whether a
    learner can recover mechanisms rather than merely fit prices.
    """

    def __init__(self, seed: int = 7, noise: float = 0.18) -> None:
        self.rng = np.random.default_rng(seed)
        self.noise = noise

    @staticmethod
    def _programs(regime: int):
        if regime == 0:
            return {
                "growth_equity": [
                    (0.65, lambda x: x[:, 0], "growth_surprise"),
                    (-1.45, lambda x: x[:, 1], "inflation_surprise"),
                    (0.75, lambda x: x[:, 2], "liquidity_shock"),
                    (-0.85, lambda x: x[:, 1] * x[:, 3], "inflation_surprise*crowding"),
                ],
                "value_equity": [
                    (0.55, lambda x: x[:, 0], "growth_surprise"),
                    (-0.55, lambda x: x[:, 1], "inflation_surprise"),
                    (0.45, lambda x: x[:, 2], "liquidity_shock"),
                    (0.22, lambda x: x[:, 4], "policy_surprise"),
                ],
                "two_year_yield": [
                    (0.25, lambda x: x[:, 0], "growth_surprise"),
                    (1.35, lambda x: x[:, 1], "inflation_surprise"),
                    (1.05, lambda x: x[:, 4], "policy_surprise"),
                ],
                "usd": [
                    (0.18, lambda x: x[:, 0], "growth_surprise"),
                    (0.72, lambda x: x[:, 1], "inflation_surprise"),
                    (0.66, lambda x: x[:, 4], "policy_surprise"),
                    (-0.28, lambda x: x[:, 2], "liquidity_shock"),
                ],
                "gold": [
                    (-0.22, lambda x: x[:, 0], "growth_surprise"),
                    (-0.42, lambda x: x[:, 4], "policy_surprise"),
                    (0.58, lambda x: x[:, 2], "liquidity_shock"),
                ],
                "volatility": [
                    (-0.28, lambda x: x[:, 0], "growth_surprise"),
                    (0.82, lambda x: x[:, 1], "inflation_surprise"),
                    (-0.82, lambda x: x[:, 2], "liquidity_shock"),
                    (0.68, lambda x: x[:, 3], "crowding"),
                    (0.52, lambda x: x[:, 1] * x[:, 3], "inflation_surprise*crowding"),
                ],
            }
        return {
            "growth_equity": [
                (0.38, lambda x: x[:, 0], "growth_surprise"),
                (-0.48, lambda x: x[:, 1], "inflation_surprise"),
                (1.48, lambda x: x[:, 2], "liquidity_shock"),
                (-1.08, lambda x: x[:, 3], "crowding"),
                (1.18, lambda x: x[:, 2] * x[:, 3], "liquidity_shock*crowding"),
            ],
            "value_equity": [
                (0.62, lambda x: x[:, 0], "growth_surprise"),
                (0.88, lambda x: x[:, 2], "liquidity_shock"),
                (-0.42, lambda x: x[:, 3], "crowding"),
            ],
            "two_year_yield": [
                (0.35, lambda x: x[:, 0], "growth_surprise"),
                (0.72, lambda x: x[:, 1], "inflation_surprise"),
                (0.58, lambda x: x[:, 4], "policy_surprise"),
                (-0.62, lambda x: x[:, 2], "liquidity_shock"),
            ],
            "usd": [
                (0.58, lambda x: x[:, 4], "policy_surprise"),
                (-0.58, lambda x: x[:, 2], "liquidity_shock"),
                (0.52, lambda x: x[:, 3], "crowding"),
            ],
            "gold": [
                (0.82, lambda x: x[:, 2], "liquidity_shock"),
                (-0.34, lambda x: x[:, 4], "policy_surprise"),
                (0.35, lambda x: x[:, 3], "crowding"),
            ],
            "volatility": [
                (-1.18, lambda x: x[:, 2], "liquidity_shock"),
                (1.22, lambda x: x[:, 3], "crowding"),
                (-0.72, lambda x: x[:, 2] * x[:, 3], "liquidity_shock*crowding"),
            ],
        }

    def generate(self, n: int = 360, switch_at: float = 0.58) -> SyntheticWorld:
        if n < 80:
            raise ValueError("n must be at least 80")
        switch_index = int(n * switch_at)
        switch_index = min(max(switch_index, 40), n)

        x = self.rng.normal(size=(n, len(FEATURES)))
        for t in range(1, n):
            x[t, 3] = 0.78 * x[t - 1, 3] + 0.62 * x[t, 3]
            x[t, 2] = 0.28 * x[t - 1, 2] + 0.96 * x[t, 2]

        regimes = np.zeros(n, dtype=int)
        regimes[switch_index:] = 1
        y = np.zeros((n, len(ASSETS)), dtype=float)
        hidden_terms: dict[int, dict[str, tuple[str, ...]]] = {0: {}, 1: {}}

        for regime in (0, 1):
            programs = self._programs(regime)
            mask = regimes == regime
            xr = x[mask]
            for asset_idx, asset in enumerate(ASSETS):
                pieces = programs[asset]
                hidden_terms[regime][asset] = tuple(piece[2] for piece in pieces)
                signal = sum(coef * fn(xr) for coef, fn, _ in pieces)
                reflexive = 0.12 * np.tanh(signal) * xr[:, 3]
                y[mask, asset_idx] = signal + reflexive + self.rng.normal(0, self.noise, size=len(xr))

        return SyntheticWorld(
            x=x,
            y=y,
            feature_names=FEATURES,
            target_names=ASSETS,
            regimes=regimes,
            switch_index=switch_index,
            hidden_terms=hidden_terms,
        )
