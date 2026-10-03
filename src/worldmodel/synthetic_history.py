from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np

from .event_data import EventDataset, EventRecord


FEATURES = (
    "surprise",
    "pre_vol",
    "positioning",
    "liquidity",
    "rates_state",
    "risk_sentiment",
)

OUTCOMES = (
    "growth_equity",
    "two_year_yield",
    "usd",
    "volatility",
)

FAMILIES = ("earnings", "inflation", "central_bank", "liquidity")


def generate_synthetic_history(
    *,
    seed: int = 7,
    n: int = 120,
    start: datetime | None = None,
) -> EventDataset:
    """Create an event dataset shaped like a sealed historical study.

    This is not historical market data. It exists to test the Phase-2 protocol,
    feature-availability rules, forecast sealing and baseline comparison end-to-end.
    """
    if n < 40:
        raise ValueError("n must be at least 40")

    rng = np.random.default_rng(seed)
    start = start or datetime(2014, 1, 15, 13, 30, tzinfo=timezone.utc)
    records: list[EventRecord] = []

    positioning = 0.0
    sentiment = 0.0
    for index in range(n):
        event_at = start + timedelta(days=21 * index)
        family = FAMILIES[index % len(FAMILIES)]
        surprise = float(rng.normal())
        pre_vol = float(abs(rng.normal(0.85, 0.25)))
        positioning = 0.72 * positioning + float(rng.normal(0, 0.55))
        liquidity = float(rng.normal())
        rates_state = float(rng.normal())
        sentiment = 0.62 * sentiment + float(rng.normal(0, 0.65))

        features = {
            "surprise": surprise,
            "pre_vol": pre_vol,
            "positioning": positioning,
            "liquidity": liquidity,
            "rates_state": rates_state,
            "risk_sentiment": sentiment,
        }

        availability = {
            "surprise": event_at,
            "pre_vol": event_at - timedelta(minutes=1),
            "positioning": event_at - timedelta(hours=1),
            "liquidity": event_at - timedelta(minutes=1),
            "rates_state": event_at - timedelta(minutes=1),
            "risk_sentiment": event_at - timedelta(minutes=1),
        }

        family_scale = {
            "earnings": 1.00,
            "inflation": 1.15,
            "central_bank": 1.10,
            "liquidity": 1.20,
        }[family]
        late_regime = 1.0 if index >= int(n * 0.70) else 0.0

        growth = (
            family_scale * 0.75 * surprise
            - 0.38 * rates_state
            + 0.44 * liquidity
            - (0.18 + 0.42 * late_regime) * positioning * pre_vol
            + 0.24 * sentiment
        )
        two_year = (
            0.72 * surprise
            + 0.58 * rates_state
            - 0.20 * liquidity
            + 0.12 * positioning
        )
        usd = (
            0.36 * surprise
            + 0.42 * rates_state
            - 0.33 * liquidity
            + 0.16 * sentiment
        )
        volatility = (
            -0.45 * surprise
            - 0.62 * liquidity
            + 0.52 * abs(positioning)
            + (0.22 + 0.48 * late_regime) * pre_vol * abs(positioning)
        )

        noise = rng.normal(0, 0.16, size=4)
        outcomes = {
            name: float(value)
            for name, value in zip(
                OUTCOMES,
                np.asarray([growth, two_year, usd, volatility]) + noise,
            )
        }

        records.append(
            EventRecord(
                event_id=f"{family}-{index:04d}",
                family=family,
                event_at=event_at,
                features=features,
                feature_available_at=availability,
                outcomes=outcomes,
            )
        )

    return EventDataset(
        records,
        feature_names=FEATURES,
        outcome_names=OUTCOMES,
    )
