from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Mapping, Sequence

import numpy as np

from .event_data import parse_timestamp
from .sealing import sha256_payload


@dataclass(frozen=True)
class ProspectiveEntry:
    event_id: str
    event_at: datetime
    created_at: datetime
    model_name: str
    outcome_names: tuple[str, ...]
    prediction: tuple[float, ...]
    metadata: Mapping[str, object]
    seal: str

    def payload(self) -> dict[str, object]:
        body = asdict(self)
        body.pop("seal")
        return body

    def verify(self) -> bool:
        return sha256_payload(self.payload()) == self.seal


@dataclass(frozen=True)
class ProspectiveScore:
    event_id: str
    mae: float
    rmse: float
    signed_error: tuple[float, ...]
    seal_valid: bool


def create_prospective_entry(
    *,
    event_id: str,
    event_at: datetime,
    created_at: datetime,
    model_name: str,
    outcome_names: Sequence[str],
    prediction: Sequence[float],
    metadata: Mapping[str, object] | None = None,
) -> ProspectiveEntry:
    event = parse_timestamp(event_at)
    created = parse_timestamp(created_at)
    if created >= event:
        raise ValueError("prospective claim must be sealed before the event")
    names = tuple(str(name) for name in outcome_names)
    values = tuple(float(value) for value in prediction)
    if len(names) != len(values) or not names:
        raise ValueError("outcome_names and prediction must be non-empty and aligned")

    body = {
        "event_id": str(event_id),
        "event_at": event,
        "created_at": created,
        "model_name": str(model_name),
        "outcome_names": names,
        "prediction": values,
        "metadata": dict(metadata or {}),
    }
    return ProspectiveEntry(**body, seal=sha256_payload(body))


def score_prospective_entry(
    entry: ProspectiveEntry,
    *,
    outcome: Sequence[float],
    observed_at: datetime,
) -> ProspectiveScore:
    observed = parse_timestamp(observed_at)
    if observed < entry.event_at:
        raise ValueError("outcome cannot be scored before the event")
    truth = np.asarray(outcome, dtype=float)
    prediction = np.asarray(entry.prediction, dtype=float)
    if truth.shape != prediction.shape:
        raise ValueError("outcome shape must match prediction")
    error = prediction - truth
    return ProspectiveScore(
        event_id=entry.event_id,
        mae=float(np.mean(np.abs(error))),
        rmse=float(np.sqrt(np.mean(error * error))),
        signed_error=tuple(float(value) for value in error),
        seal_valid=entry.verify(),
    )
