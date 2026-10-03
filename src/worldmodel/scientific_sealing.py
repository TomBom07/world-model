from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .event_data import parse_timestamp
from .sealing import sha256_payload


@dataclass(frozen=True)
class ScientificClaimSeal:
    experiment_name: str
    code_ref: str
    data_cutoff: datetime
    created_at: datetime
    ontology: Mapping[str, Any]
    hypotheses: Mapping[str, Any]
    posterior: Mapping[str, float]
    selected_query: Mapping[str, Any]
    preregistered_predictions: Mapping[str, Any]
    evaluation_protocol: Mapping[str, Any]
    seal: str

    def payload(self) -> dict[str, Any]:
        body = asdict(self)
        body.pop("seal")
        return body

    def verify(self) -> bool:
        return sha256_payload(self.payload()) == self.seal


def seal_scientific_claim(
    *,
    experiment_name: str,
    code_ref: str,
    data_cutoff: datetime,
    ontology: Mapping[str, Any],
    hypotheses: Mapping[str, Any],
    posterior: Mapping[str, float],
    selected_query: Mapping[str, Any],
    preregistered_predictions: Mapping[str, Any],
    evaluation_protocol: Mapping[str, Any],
    created_at: datetime | None = None,
) -> ScientificClaimSeal:
    cutoff = parse_timestamp(data_cutoff)
    created = parse_timestamp(created_at or datetime.now(timezone.utc))
    if created < cutoff:
        raise ValueError("claim cannot be sealed before its declared data cutoff")

    payload = {
        "experiment_name": str(experiment_name),
        "code_ref": str(code_ref),
        "data_cutoff": cutoff,
        "created_at": created,
        "ontology": dict(ontology),
        "hypotheses": dict(hypotheses),
        "posterior": {str(k): float(v) for k, v in posterior.items()},
        "selected_query": dict(selected_query),
        "preregistered_predictions": dict(preregistered_predictions),
        "evaluation_protocol": dict(evaluation_protocol),
    }
    return ScientificClaimSeal(**payload, seal=sha256_payload(payload))
