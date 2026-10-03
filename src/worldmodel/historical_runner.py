from __future__ import annotations

from dataclasses import asdict, dataclass
from math import log, pi
from typing import Mapping, Sequence

import numpy as np

from .event_data import EventDataset, EventRecord
from .historical_models import FingerprintModel, build_historical_models
from .sealing import ExperimentSpec, ForecastSeal, SealedManifest, seal_forecast


@dataclass(frozen=True)
class ModelMetrics:
    mae: float
    rmse: float
    directional_accuracy: float
    mean_log_score: float
    interval_coverage_80: float


def _score(
    truth: np.ndarray,
    mean: np.ndarray,
    sigma: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
) -> ModelMetrics:
    truth = np.asarray(truth, dtype=float)
    mean = np.asarray(mean, dtype=float)
    sigma = np.maximum(np.asarray(sigma, dtype=float), 1e-6)
    error = truth - mean
    mae = float(np.mean(np.abs(error)))
    rmse = float(np.sqrt(np.mean(error**2)))
    directional = float(np.mean(np.sign(truth) == np.sign(mean)))
    log_score = -0.5 * ((error / sigma) ** 2 + np.log(2 * pi * sigma**2))
    coverage = float(np.mean((truth >= low) & (truth <= high)))
    return ModelMetrics(
        mae=mae,
        rmse=rmse,
        directional_accuracy=directional,
        mean_log_score=float(np.mean(log_score)),
        interval_coverage_80=coverage,
    )


class SealedHistoricalRunner:
    """Leakage-checked, frozen historical replay.

    The model stack is trained only on rows ending on or before training_end. During
    evaluation every forecast is created from a redacted ForecastEvent and sealed
    before the corresponding outcome vector is read for scoring.
    """

    def __init__(
        self,
        dataset: EventDataset,
        spec: ExperimentSpec,
        *,
        seed: int = 7,
        models: Mapping[str, FingerprintModel] | None = None,
        code_ref: str = "uncommitted",
    ) -> None:
        self.dataset = dataset
        self.spec = spec
        self.seed = int(seed)
        self.models = dict(models or build_historical_models(seed))
        self.code_ref = str(code_ref)

    def _rows(self) -> tuple[tuple[EventRecord, ...], tuple[EventRecord, ...]]:
        families: Sequence[str] | None = (
            self.spec.event_families if self.spec.event_families else None
        )
        train = self.dataset.select(
            end=self.spec.training_end,
            families=families,
        )
        evaluation = self.dataset.select(
            start=self.spec.evaluation_start,
            end=self.spec.evaluation_end,
            families=families,
        )
        if len(train) < 12:
            raise ValueError("At least 12 training events are required")
        if not evaluation:
            raise ValueError("Evaluation period contains no events")
        return train, evaluation

    def run(self) -> dict[str, object]:
        self.dataset.assert_no_leakage()
        if tuple(self.dataset.feature_names) != tuple(self.spec.feature_names):
            raise ValueError("Dataset features do not match the sealed experiment spec")
        if tuple(self.dataset.outcome_names) != tuple(self.spec.outcome_names):
            raise ValueError("Dataset outcomes do not match the sealed experiment spec")

        train_rows, evaluation_rows = self._rows()
        x_train, y_train = self.dataset.matrices(train_rows)

        schema = {
            "feature_names": self.dataset.feature_names,
            "outcome_names": self.dataset.outcome_names,
            "event_families": sorted({row.family for row in self.dataset.records}),
            "record_count": len(self.dataset.records),
        }
        dataset_payload = [
            {
                "event_id": row.event_id,
                "family": row.family,
                "event_at": row.event_at,
                "features": dict(row.features),
                "feature_available_at": dict(row.feature_available_at),
                "outcomes": dict(row.outcomes),
            }
            for row in self.dataset.records
        ]
        manifest = SealedManifest.create(
            self.spec,
            dataset_schema=schema,
            dataset_payload=dataset_payload,
            code_ref=self.code_ref,
            created_at=self.spec.evaluation_start,
        )

        fitted: dict[str, FingerprintModel] = {}
        for name, model in self.models.items():
            fitted[name] = model.fit(
                x_train,
                y_train,
                self.spec.feature_names,
                self.spec.outcome_names,
            )

        forecast_seals: dict[str, list[ForecastSeal]] = {
            name: [] for name in fitted
        }
        predictions: dict[str, list[np.ndarray]] = {name: [] for name in fitted}
        sigmas: dict[str, list[np.ndarray]] = {name: [] for name in fitted}
        lows: dict[str, list[np.ndarray]] = {name: [] for name in fitted}
        highs: dict[str, list[np.ndarray]] = {name: [] for name in fitted}
        truths: list[np.ndarray] = []

        for row in evaluation_rows:
            view = row.forecast_view(self.spec.feature_names)
            x_event = view.vector(self.spec.feature_names)[None, :]

            event_predictions: dict[str, object] = {}
            for name, model in fitted.items():
                bundle = model.predict(x_event)
                mean = bundle.mean[0]
                low = bundle.low[0]
                high = bundle.high[0]
                sigma = bundle.sigma[0]
                seal = seal_forecast(
                    view,
                    spec=self.spec,
                    model_name=name,
                    outcome_names=self.spec.outcome_names,
                    prediction=mean,
                    interval_low=low,
                    interval_high=high,
                    created_at=row.event_at,
                )
                if not seal.verify():
                    raise RuntimeError(f"Forecast seal failed verification for {row.event_id}")

                forecast_seals[name].append(seal)
                predictions[name].append(mean)
                lows[name].append(low)
                highs[name].append(high)
                sigmas[name].append(sigma)
                event_predictions[name] = bundle

            # Outcome access occurs only after all forecasts for this event are sealed.
            truths.append(row.outcome_vector(self.spec.outcome_names))

        truth_matrix = np.vstack(truths)
        metrics: dict[str, dict[str, float]] = {}
        for name in fitted:
            model_metrics = _score(
                truth_matrix,
                np.vstack(predictions[name]),
                np.vstack(sigmas[name]),
                np.vstack(lows[name]),
                np.vstack(highs[name]),
            )
            metrics[name] = asdict(model_metrics)

        rmc = fitted.get("rmc")
        programs = rmc.programs() if rmc is not None and hasattr(rmc, "programs") else []

        return {
            "manifest": {
                **asdict(manifest),
                "seal": manifest.seal,
            },
            "spec": {
                **asdict(self.spec),
                "hash": self.spec.hash,
            },
            "audit": {
                "leakage_violations": 0,
                "training_events": len(train_rows),
                "evaluation_events": len(evaluation_rows),
                "first_training_event": train_rows[0].event_at,
                "last_training_event": train_rows[-1].event_at,
                "first_evaluation_event": evaluation_rows[0].event_at,
                "last_evaluation_event": evaluation_rows[-1].event_at,
                "all_forecast_seals_valid": all(
                    seal.verify()
                    for seals in forecast_seals.values()
                    for seal in seals
                ),
            },
            "metrics": metrics,
            "rmc_programs": programs,
            "forecasts": {
                name: [
                    {
                        "event_id": seal.event_id,
                        "event_at": seal.event_at,
                        "prediction": list(seal.prediction),
                        "low": list(seal.interval_low),
                        "high": list(seal.interval_high),
                        "feature_hash": seal.feature_hash,
                        "seal": seal.seal,
                    }
                    for seal in seals
                ]
                for name, seals in forecast_seals.items()
            },
            "outcome_names": list(self.spec.outcome_names),
            "scientific_boundary": (
                "A sealed historical replay reduces look-ahead and tuning risk, but it "
                "does not by itself establish causality or live trading alpha."
            ),
        }
