from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .event_data import ForecastEvent, parse_timestamp


def _normalize(value: Any) -> Any:
    if isinstance(value, datetime):
        return parse_timestamp(value).isoformat()
    if isinstance(value, np.ndarray):
        return [_normalize(item) for item in value.tolist()]
    if isinstance(value, Mapping):
        return {str(key): _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def sha256_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExperimentSpec:
    name: str
    training_end: datetime
    evaluation_start: datetime
    evaluation_end: datetime
    event_families: tuple[str, ...]
    feature_names: tuple[str, ...]
    outcome_names: tuple[str, ...]
    model_config: Mapping[str, Any] = field(default_factory=dict)
    protocol_version: str = "sealed-history-v1"

    def __post_init__(self) -> None:
        training_end = parse_timestamp(self.training_end)
        evaluation_start = parse_timestamp(self.evaluation_start)
        evaluation_end = parse_timestamp(self.evaluation_end)
        object.__setattr__(self, "training_end", training_end)
        object.__setattr__(self, "evaluation_start", evaluation_start)
        object.__setattr__(self, "evaluation_end", evaluation_end)
        if not training_end < evaluation_start <= evaluation_end:
            raise ValueError(
                "Expected training_end < evaluation_start <= evaluation_end"
            )

    @property
    def hash(self) -> str:
        return sha256_payload(asdict(self))


@dataclass(frozen=True)
class SealedManifest:
    spec_hash: str
    dataset_schema_hash: str
    dataset_hash: str
    code_ref: str
    created_at: datetime
    protocol_version: str = "sealed-history-v1"

    @property
    def seal(self) -> str:
        return sha256_payload(asdict(self))

    @classmethod
    def create(
        cls,
        spec: ExperimentSpec,
        *,
        dataset_schema: Mapping[str, Any],
        dataset_payload: Any,
        code_ref: str,
        created_at: datetime | None = None,
    ) -> "SealedManifest":
        return cls(
            spec_hash=spec.hash,
            dataset_schema_hash=sha256_payload(dataset_schema),
            dataset_hash=sha256_payload(dataset_payload),
            code_ref=str(code_ref),
            created_at=parse_timestamp(created_at or datetime.now(timezone.utc)),
        )


@dataclass(frozen=True)
class ForecastSeal:
    event_id: str
    event_at: datetime
    created_at: datetime
    spec_hash: str
    model_name: str
    feature_hash: str
    prediction: tuple[float, ...]
    interval_low: tuple[float, ...]
    interval_high: tuple[float, ...]
    outcome_names: tuple[str, ...]
    seal: str

    def verify(self) -> bool:
        payload = {
            "event_id": self.event_id,
            "event_at": self.event_at,
            "created_at": self.created_at,
            "spec_hash": self.spec_hash,
            "model_name": self.model_name,
            "feature_hash": self.feature_hash,
            "prediction": self.prediction,
            "interval_low": self.interval_low,
            "interval_high": self.interval_high,
            "outcome_names": self.outcome_names,
        }
        return sha256_payload(payload) == self.seal


def seal_forecast(
    event: ForecastEvent,
    *,
    spec: ExperimentSpec,
    model_name: str,
    outcome_names: Sequence[str],
    prediction: Sequence[float],
    interval_low: Sequence[float],
    interval_high: Sequence[float],
    created_at: datetime | None = None,
) -> ForecastSeal:
    created = parse_timestamp(created_at or event.event_at)
    if created > event.event_at:
        raise ValueError(
            "Forecast seal must be created no later than the event cutoff in historical replay"
        )

    feature_payload = {
        "event_id": event.event_id,
        "event_at": event.event_at,
        "features": dict(event.features),
    }
    body = {
        "event_id": event.event_id,
        "event_at": event.event_at,
        "created_at": created,
        "spec_hash": spec.hash,
        "model_name": str(model_name),
        "feature_hash": sha256_payload(feature_payload),
        "prediction": tuple(float(x) for x in prediction),
        "interval_low": tuple(float(x) for x in interval_low),
        "interval_high": tuple(float(x) for x in interval_high),
        "outcome_names": tuple(outcome_names),
    }
    return ForecastSeal(**body, seal=sha256_payload(body))
