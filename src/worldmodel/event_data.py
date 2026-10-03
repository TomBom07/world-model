from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import csv
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np


def parse_timestamp(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class ForecastEvent:
    event_id: str
    family: str
    event_at: datetime
    features: Mapping[str, float]

    def vector(self, names: Sequence[str]) -> np.ndarray:
        return np.asarray([float(self.features[name]) for name in names], dtype=float)


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    family: str
    event_at: datetime
    features: Mapping[str, float]
    feature_available_at: Mapping[str, datetime]
    outcomes: Mapping[str, float]

    def forecast_view(self, feature_names: Sequence[str]) -> ForecastEvent:
        return ForecastEvent(
            event_id=self.event_id,
            family=self.family,
            event_at=self.event_at,
            features={name: float(self.features[name]) for name in feature_names},
        )

    def outcome_vector(self, names: Sequence[str]) -> np.ndarray:
        return np.asarray([float(self.outcomes[name]) for name in names], dtype=float)


@dataclass(frozen=True)
class LeakageViolation:
    event_id: str
    feature: str
    event_at: datetime
    available_at: datetime

    @property
    def delay_seconds(self) -> float:
        return float((self.available_at - self.event_at).total_seconds())


class EventDataset:
    """Timestamped event data with explicit feature availability.

    A feature is permitted for an event forecast only when its availability
    timestamp is no later than the event cutoff. This makes look-ahead leakage a
    schema-level error rather than a modeling convention.
    """

    def __init__(
        self,
        records: Iterable[EventRecord],
        *,
        feature_names: Sequence[str],
        outcome_names: Sequence[str],
    ) -> None:
        self.records = tuple(sorted(records, key=lambda row: (row.event_at, row.event_id)))
        self.feature_names = tuple(feature_names)
        self.outcome_names = tuple(outcome_names)
        self._validate_schema()

    def _validate_schema(self) -> None:
        ids: set[str] = set()
        for row in self.records:
            if row.event_id in ids:
                raise ValueError(f"Duplicate event_id: {row.event_id}")
            ids.add(row.event_id)
            missing_features = set(self.feature_names) - set(row.features)
            missing_availability = set(self.feature_names) - set(row.feature_available_at)
            missing_outcomes = set(self.outcome_names) - set(row.outcomes)
            if missing_features:
                raise ValueError(f"{row.event_id}: missing features {sorted(missing_features)}")
            if missing_availability:
                raise ValueError(
                    f"{row.event_id}: missing feature availability {sorted(missing_availability)}"
                )
            if missing_outcomes:
                raise ValueError(f"{row.event_id}: missing outcomes {sorted(missing_outcomes)}")

    def leakage_violations(self) -> list[LeakageViolation]:
        violations: list[LeakageViolation] = []
        for row in self.records:
            for feature in self.feature_names:
                available = parse_timestamp(row.feature_available_at[feature])
                if available > row.event_at:
                    violations.append(
                        LeakageViolation(
                            event_id=row.event_id,
                            feature=feature,
                            event_at=row.event_at,
                            available_at=available,
                        )
                    )
        return violations

    def assert_no_leakage(self) -> None:
        violations = self.leakage_violations()
        if not violations:
            return
        preview = ", ".join(
            f"{v.event_id}:{v.feature}(+{v.delay_seconds:.0f}s)"
            for v in violations[:5]
        )
        raise ValueError(
            f"Look-ahead leakage detected in {len(violations)} feature values: {preview}"
        )

    def select(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        families: Sequence[str] | None = None,
    ) -> tuple[EventRecord, ...]:
        start = parse_timestamp(start) if start is not None else None
        end = parse_timestamp(end) if end is not None else None
        allowed = set(families) if families else None
        return tuple(
            row
            for row in self.records
            if (start is None or row.event_at >= start)
            and (end is None or row.event_at <= end)
            and (allowed is None or row.family in allowed)
        )

    def matrices(
        self,
        rows: Sequence[EventRecord],
    ) -> tuple[np.ndarray, np.ndarray]:
        x = np.asarray(
            [[float(row.features[name]) for name in self.feature_names] for row in rows],
            dtype=float,
        )
        y = np.asarray(
            [[float(row.outcomes[name]) for name in self.outcome_names] for row in rows],
            dtype=float,
        )
        return x, y

    def to_csv(self, path: str | Path) -> None:
        fieldnames = ["event_id", "family", "event_at"]
        for name in self.feature_names:
            fieldnames.extend([f"x_{name}", f"x_{name}__available_at"])
        for name in self.outcome_names:
            fieldnames.append(f"y_{name}")

        with Path(path).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.records:
                payload: dict[str, object] = {
                    "event_id": row.event_id,
                    "family": row.family,
                    "event_at": row.event_at.isoformat(),
                }
                for name in self.feature_names:
                    payload[f"x_{name}"] = float(row.features[name])
                    payload[f"x_{name}__available_at"] = parse_timestamp(
                        row.feature_available_at[name]
                    ).isoformat()
                for name in self.outcome_names:
                    payload[f"y_{name}"] = float(row.outcomes[name])
                writer.writerow(payload)

    @classmethod
    def from_csv(
        cls,
        path: str | Path,
        *,
        feature_names: Sequence[str],
        outcome_names: Sequence[str],
    ) -> "EventDataset":
        records: list[EventRecord] = []
        with Path(path).open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            required = {"event_id", "family", "event_at"}
            missing = required - set(reader.fieldnames or ())
            if missing:
                raise ValueError(f"CSV missing required columns: {sorted(missing)}")

            for raw in reader:
                event_at = parse_timestamp(raw["event_at"])
                features: dict[str, float] = {}
                availability: dict[str, datetime] = {}
                outcomes: dict[str, float] = {}

                for name in feature_names:
                    features[name] = float(raw[f"x_{name}"])
                    availability[name] = parse_timestamp(raw[f"x_{name}__available_at"])
                for name in outcome_names:
                    outcomes[name] = float(raw[f"y_{name}"])

                records.append(
                    EventRecord(
                        event_id=str(raw["event_id"]),
                        family=str(raw["family"]),
                        event_at=event_at,
                        features=features,
                        feature_available_at=availability,
                        outcomes=outcomes,
                    )
                )

        return cls(
            records,
            feature_names=feature_names,
            outcome_names=outcome_names,
        )
