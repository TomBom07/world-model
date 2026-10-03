from __future__ import annotations

from datetime import date, datetime, time, timezone
from math import log
from typing import Callable

import numpy as np

from .event_data import EventDataset, EventRecord
from .fred import FredSeries, download_fred_series


FEATURES = (
    "policy_delta",
    "policy_midpoint",
    "pre_growth_momentum_5d",
    "pre_vix",
    "pre_2y",
    "pre_usd_momentum_5d",
)

OUTCOMES = (
    "growth_equity",
    "two_year_yield",
    "usd",
    "volatility",
)

SERIES = {
    "upper": "DFEDTARU",
    "lower": "DFEDTARL",
    "legacy": "DFEDTAR",
    "nasdaq": "NASDAQCOM",
    "two_year": "DGS2",
    "usd": "DTWEXBGS",
    "vix": "VIXCLS",
}


def _merged_target(
    upper: FredSeries,
    lower: FredSeries,
    legacy: FredSeries,
) -> FredSeries:
    values: dict[date, float] = dict(legacy.values)
    common_range_dates = set(upper.values) & set(lower.values)
    for day in common_range_dates:
        values[day] = 0.5 * (upper.values[day] + lower.values[day])
    return FredSeries(series_id="FED_TARGET_MIDPOINT", values=values)


def _common_market_dates(series: list[FredSeries]) -> list[date]:
    common = set(series[0].values)
    for item in series[1:]:
        common &= set(item.values)
    return sorted(common)


def _previous_common(common_dates: list[date], day: date) -> date | None:
    candidates = [candidate for candidate in common_dates if candidate < day]
    return max(candidates) if candidates else None


def _first_common_on_or_after(common_dates: list[date], day: date) -> date | None:
    candidates = [candidate for candidate in common_dates if candidate >= day]
    return min(candidates) if candidates else None


def _nth_previous(common_dates: list[date], day: date, n: int) -> date | None:
    candidates = [candidate for candidate in common_dates if candidate < day]
    if len(candidates) < n:
        return None
    return candidates[-n]


def build_fed_target_change_dataset(
    *,
    start: date = date(1994, 1, 1),
    end: date | None = None,
    fetch_text: Callable[[str], str] | None = None,
) -> EventDataset:
    """Build a real-data bootstrap dataset around Fed target-rate changes.

    This intentionally uses **effective target-change dates** inferred from FRED, not
    exact intraday FOMC announcement timestamps. Market state features come from the
    last common close before the effective date; outcomes run from that pre-event close
    to the first common close on/after the effective date.

    The dataset is useful for plumbing and sealed historical research, but the timing is
    too coarse for any claim about immediate announcement alpha.
    """
    loaded = {
        key: download_fred_series(series_id, start=start, end=end, fetch_text=fetch_text)
        for key, series_id in SERIES.items()
    }
    target = _merged_target(loaded["upper"], loaded["lower"], loaded["legacy"])

    market_series = [
        loaded["nasdaq"],
        loaded["two_year"],
        loaded["usd"],
        loaded["vix"],
    ]
    common_dates = _common_market_dates(market_series)
    records: list[EventRecord] = []

    for event_day, old_target, new_target in target.changes():
        if event_day < start or (end is not None and event_day > end):
            continue

        pre_day = _previous_common(common_dates, event_day)
        post_day = _first_common_on_or_after(common_dates, event_day)
        pre_5 = _nth_previous(common_dates, event_day, 5)
        if pre_day is None or post_day is None or pre_5 is None:
            continue

        nasdaq_pre = loaded["nasdaq"].values[pre_day]
        nasdaq_pre5 = loaded["nasdaq"].values[pre_5]
        nasdaq_post = loaded["nasdaq"].values[post_day]

        usd_pre = loaded["usd"].values[pre_day]
        usd_pre5 = loaded["usd"].values[pre_5]
        usd_post = loaded["usd"].values[post_day]

        two_pre = loaded["two_year"].values[pre_day]
        two_post = loaded["two_year"].values[post_day]

        vix_pre = loaded["vix"].values[pre_day]
        vix_post = loaded["vix"].values[post_day]

        cutoff = datetime.combine(event_day, time(18, 0), tzinfo=timezone.utc)
        pre_close_available = datetime.combine(
            pre_day,
            time(23, 59, 59),
            tzinfo=timezone.utc,
        )

        features = {
            "policy_delta": float(new_target - old_target),
            "policy_midpoint": float(new_target),
            "pre_growth_momentum_5d": float(log(nasdaq_pre / nasdaq_pre5)),
            "pre_vix": float(vix_pre),
            "pre_2y": float(two_pre),
            "pre_usd_momentum_5d": float(log(usd_pre / usd_pre5)),
        }
        availability = {
            "policy_delta": cutoff,
            "policy_midpoint": cutoff,
            "pre_growth_momentum_5d": pre_close_available,
            "pre_vix": pre_close_available,
            "pre_2y": pre_close_available,
            "pre_usd_momentum_5d": pre_close_available,
        }
        outcomes = {
            "growth_equity": float(log(nasdaq_post / nasdaq_pre)),
            "two_year_yield": float(two_post - two_pre),
            "usd": float(log(usd_post / usd_pre)),
            "volatility": float(vix_post - vix_pre),
        }

        records.append(
            EventRecord(
                event_id=f"fed-target-{event_day.isoformat()}",
                family="fed_target_change",
                event_at=cutoff,
                features=features,
                feature_available_at=availability,
                outcomes=outcomes,
            )
        )

    if not records:
        raise ValueError("No Fed target-change events could be constructed")

    dataset = EventDataset(
        records,
        feature_names=FEATURES,
        outcome_names=OUTCOMES,
    )
    dataset.assert_no_leakage()
    return dataset
