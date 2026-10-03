from __future__ import annotations

from dataclasses import dataclass

import numpy as np


ASSETS = ("growth_equity", "value_equity", "two_year_yield", "volatility")
EVENTS = ("growth", "inflation", "liquidity", "policy", "sentiment")
AGENTS = ("fundamental", "macro", "momentum", "retail", "leveraged", "dealer")
MECHANISMS = ("belief_reflexive", "liquidity_reflexive")

_EVENT_LOADINGS = np.array(
    [
        [0.85, -0.90, 0.65, -0.45, 0.50],
        [0.70, -0.35, 0.45, -0.15, 0.30],
        [0.25, 1.00, -0.35, 0.85, -0.05],
        [-0.30, 0.60, -0.75, 0.30, 0.40],
    ],
    dtype=float,
)

_POPULATION_WEIGHTS = np.array([0.23, 0.18, 0.17, 0.12, 0.20, 0.10], dtype=float)

_MECHANISM_CONFIG = {
    "belief_reflexive": {
        "higher_order": 1.05,
        "liquidity": 0.35,
        "leverage": 0.60,
        "dealer_gamma": -0.35,
        "price_impact": 0.18,
    },
    "liquidity_reflexive": {
        "higher_order": 0.35,
        "liquidity": 1.15,
        "leverage": 1.15,
        "dealer_gamma": -0.85,
        "price_impact": 0.18,
    },
}


@dataclass(frozen=True)
class StrategicWorld:
    mechanism: str
    events: np.ndarray
    returns: np.ndarray
    prices: np.ndarray
    first_order_beliefs: np.ndarray
    second_order_beliefs: np.ndarray
    demands: np.ndarray
    leverage: np.ndarray
    margin_calls: np.ndarray
    dealer_hedge: np.ndarray
    market_belief: np.ndarray
    feature_names: tuple[str, ...] = EVENTS
    asset_names: tuple[str, ...] = ASSETS
    agent_names: tuple[str, ...] = AGENTS

    def asset(self, name: str) -> np.ndarray:
        return self.returns[:, self.asset_names.index(name)]

    @property
    def margin_call_count(self) -> int:
        return int(self.margin_calls.sum())


class StrategicMarketSimulator:
    """Multi-population synthetic market with private and higher-order beliefs.

    Two mechanisms intentionally share most observable dynamics:
    - belief_reflexive: prices are more sensitive to beliefs about other participants.
    - liquidity_reflexive: prices are more sensitive to liquidity, leverage and dealer hedging.

    This creates an identification problem: ordinary price history can look almost the
    same while a diagnostic event produces different cross-asset reaction fingerprints.
    """

    def __init__(self, seed: int = 7, noise: float = 0.08) -> None:
        self.seed = int(seed)
        self.noise = float(noise)

    def generate_events(self, n: int) -> np.ndarray:
        if n < 32:
            raise ValueError("n must be at least 32")
        rng = np.random.default_rng(self.seed + 991)
        events = rng.normal(size=(n, len(EVENTS)))
        for t in range(1, n):
            events[t, 2] = 0.55 * events[t - 1, 2] + 0.84 * events[t, 2]
            events[t, 4] = 0.45 * events[t - 1, 4] + 0.89 * events[t, 4]
        return events

    @staticmethod
    def _validate_mechanism(mechanism: str) -> None:
        if mechanism not in MECHANISMS:
            raise ValueError(f"Unknown mechanism {mechanism!r}. Expected one of {MECHANISMS}")

    def simulate(
        self,
        mechanism: str,
        *,
        n: int = 260,
        events: np.ndarray | None = None,
        diagnostic: tuple[int, str, float] | None = None,
    ) -> StrategicWorld:
        self._validate_mechanism(mechanism)
        if events is None:
            events = self.generate_events(n)
        else:
            events = np.asarray(events, dtype=float).copy()
            n = len(events)
        if events.shape != (n, len(EVENTS)):
            raise ValueError(f"events must have shape ({n}, {len(EVENTS)})")

        if diagnostic is not None:
            index, kind, magnitude = diagnostic
            if kind not in EVENTS:
                raise ValueError(f"Unknown event kind {kind!r}")
            if not 0 <= index < n:
                raise ValueError("diagnostic index outside simulation")
            events[index, EVENTS.index(kind)] += float(magnitude)

        cfg = _MECHANISM_CONFIG[mechanism]
        rng = np.random.default_rng(self.seed)
        a = len(AGENTS)
        k = len(ASSETS)

        returns = np.zeros((n, k), dtype=float)
        prices = np.zeros((n, k), dtype=float)
        first = np.zeros((n, a, k), dtype=float)
        second = np.zeros_like(first)
        demands = np.zeros_like(first)
        leverage = np.ones((n, a), dtype=float)
        margin_calls = np.zeros((n, a), dtype=bool)
        dealer_hedge = np.zeros((n, k), dtype=float)
        market_belief = np.zeros((n, k), dtype=float)

        live_leverage = np.ones(a, dtype=float)

        for t in range(n):
            public = _EVENT_LOADINGS @ events[t]
            momentum = returns[max(0, t - 4) : t].mean(axis=0) if t else np.zeros(k)
            previous = returns[t - 1] if t else np.zeros(k)

            beliefs = np.zeros((a, k), dtype=float)
            beliefs[0] = public + rng.normal(0, 0.12, k)
            beliefs[1] = (
                0.85 * public
                + np.array([-0.15, -0.10, 0.25, 0.10]) * events[t, 1]
                + rng.normal(0, 0.14, k)
            )
            beliefs[2] = 0.30 * public + 0.95 * momentum + rng.normal(0, 0.15, k)
            beliefs[3] = (
                0.25 * public
                + 0.75 * events[t, 4] * np.array([1.0, 0.5, 0.0, 0.6])
                + 0.50 * momentum
                + rng.normal(0, 0.20, k)
            )
            beliefs[4] = 0.45 * public + 0.75 * momentum + rng.normal(0, 0.18, k)
            beliefs[5] = 0.15 * public - 0.35 * previous + rng.normal(0, 0.12, k)
            first[t] = beliefs

            consensus = (_POPULATION_WEIGHTS[:, None] * beliefs).sum(axis=0)
            market_belief[t] = consensus

            second_beliefs = np.vstack(
                [
                    consensus + rng.normal(0, 0.10 + 0.03 * i, k)
                    for i in range(a)
                ]
            )
            second_beliefs[2] += 0.30 * momentum
            second_beliefs[3] += 0.25 * momentum
            second_beliefs[5] -= 0.20 * previous
            second[t] = second_beliefs

            order = np.zeros((a, k), dtype=float)
            h = float(cfg["higher_order"])
            order[0] = 0.65 * beliefs[0] + h * 0.18 * second_beliefs[0]
            order[1] = 0.60 * beliefs[1] + h * 0.22 * second_beliefs[1]
            order[2] = 0.75 * beliefs[2] + h * 0.50 * second_beliefs[2]
            order[3] = 0.70 * beliefs[3] + h * 0.55 * second_beliefs[3]

            liquidity_stress = max(0.0, -float(events[t, 2]))
            pnl_proxy = float(np.mean(previous)) if t else 0.0
            desired_leverage = 1.2 + float(cfg["leverage"]) * (
                0.8 + 0.5 * np.tanh(events[t, 4])
            )
            if pnl_proxy < -0.60 or liquidity_stress > 1.80:
                desired_leverage = max(
                    0.25,
                    desired_leverage
                    * (0.35 if mechanism == "liquidity_reflexive" else 0.55),
                )
                margin_calls[t, 4] = True
            live_leverage[4] = 0.72 * live_leverage[4] + 0.28 * desired_leverage
            leverage[t] = live_leverage
            order[4] = live_leverage[4] * (
                0.65 * beliefs[4] + h * 0.35 * second_beliefs[4]
            )

            hedge = float(cfg["dealer_gamma"]) * previous * (1.0 + 0.40 * liquidity_stress)
            dealer_hedge[t] = hedge
            order[5] = 0.22 * beliefs[5] + hedge
            demands[t] = order

            aggregate_order = (_POPULATION_WEIGHTS[:, None] * order).sum(axis=0)
            liquidity_flow = float(cfg["liquidity"]) * events[t, 2] * np.array(
                [0.72, 0.50, -0.28, -0.68]
            )

            common = 0.72 * public
            step_return = (
                common
                + float(cfg["price_impact"]) * aggregate_order
                + 0.16 * liquidity_flow
                + rng.normal(0, self.noise, k)
            )
            returns[t] = step_return
            prices[t] = (prices[t - 1] if t else np.zeros(k)) + step_return

        return StrategicWorld(
            mechanism=mechanism,
            events=events,
            returns=returns,
            prices=prices,
            first_order_beliefs=first,
            second_order_beliefs=second,
            demands=demands,
            leverage=leverage,
            margin_calls=margin_calls,
            dealer_hedge=dealer_hedge,
            market_belief=market_belief,
        )

    def paired_worlds(self, n: int = 260) -> tuple[StrategicWorld, StrategicWorld]:
        events = self.generate_events(n)
        return (
            self.simulate("belief_reflexive", events=events),
            self.simulate("liquidity_reflexive", events=events),
        )

    def counterfactual_fingerprint(
        self,
        mechanism: str,
        *,
        events: np.ndarray,
        event_index: int,
        event_kind: str,
        magnitude: float,
        horizon: int = 3,
    ) -> np.ndarray:
        baseline = self.simulate(mechanism, events=events)
        shocked = self.simulate(
            mechanism,
            events=events,
            diagnostic=(event_index, event_kind, magnitude),
        )
        end = min(len(events), event_index + max(1, int(horizon)))
        return (shocked.returns[event_index:end] - baseline.returns[event_index:end]).sum(axis=0)
