from dataclasses import replace
from datetime import timedelta

import pytest

from worldmodel.event_data import EventDataset
from worldmodel.historical_engine import HistoricalResearchEngine
from worldmodel.historical_models import (
    LocalLevelFingerprintModel,
    SklearnFingerprintModel,
)
from worldmodel.historical_runner import SealedHistoricalRunner
from worldmodel.sealing import ExperimentSpec, seal_forecast
from worldmodel.synthetic_history import generate_synthetic_history

from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def _spec(dataset, split_index=32):
    return ExperimentSpec(
        name="test-sealed-run",
        training_end=dataset.records[split_index].event_at,
        evaluation_start=dataset.records[split_index + 1].event_at,
        evaluation_end=dataset.records[-1].event_at,
        event_families=(),
        feature_names=dataset.feature_names,
        outcome_names=dataset.outcome_names,
        model_config={"freeze": True},
    )


def test_feature_availability_leakage_is_rejected():
    dataset = generate_synthetic_history(seed=3, n=50)
    target = dataset.records[10]
    availability = dict(target.feature_available_at)
    availability["positioning"] = target.event_at + timedelta(seconds=1)

    corrupted = replace(target, feature_available_at=availability)
    rows = list(dataset.records)
    rows[10] = corrupted
    leaked = EventDataset(
        rows,
        feature_names=dataset.feature_names,
        outcome_names=dataset.outcome_names,
    )

    violations = leaked.leakage_violations()
    assert len(violations) == 1
    assert violations[0].feature == "positioning"
    with pytest.raises(ValueError, match="Look-ahead leakage"):
        leaked.assert_no_leakage()


def test_experiment_hash_is_order_stable_and_configuration_sensitive():
    dataset = generate_synthetic_history(seed=4, n=50)
    spec_a = _spec(dataset)
    spec_b = replace(spec_a, model_config={"freeze": True})
    spec_c = replace(spec_a, model_config={"freeze": False})

    assert spec_a.hash == spec_b.hash
    assert spec_a.hash != spec_c.hash


def test_forecast_seal_detects_tampering():
    dataset = generate_synthetic_history(seed=5, n=50)
    spec = _spec(dataset)
    event = dataset.records[spec.feature_names.index("surprise")].forecast_view(
        spec.feature_names
    )
    seal = seal_forecast(
        event,
        spec=spec,
        model_name="test",
        outcome_names=spec.outcome_names,
        prediction=[0.1, 0.2, 0.3, 0.4],
        interval_low=[-0.1, 0.0, 0.1, 0.2],
        interval_high=[0.3, 0.4, 0.5, 0.6],
        created_at=event.event_at,
    )
    assert seal.verify()

    tampered = replace(seal, prediction=(9.0, 0.2, 0.3, 0.4))
    assert not tampered.verify()


def test_runner_seals_forecasts_before_scoring():
    dataset = generate_synthetic_history(seed=6, n=56)
    spec = _spec(dataset, split_index=36)
    models = {
        "ridge": SklearnFingerprintModel(
            "ridge",
            make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        ),
        "local_level": LocalLevelFingerprintModel(),
    }
    report = SealedHistoricalRunner(
        dataset,
        spec,
        models=models,
        code_ref="test-code-ref",
    ).run()

    assert report["audit"]["leakage_violations"] == 0
    assert report["audit"]["all_forecast_seals_valid"] is True
    assert report["audit"]["last_training_event"] < report["audit"]["first_evaluation_event"]
    assert report["manifest"]["dataset_hash"]
    assert report["manifest"]["seal"]
    assert set(report["metrics"]) == {"ridge", "local_level"}
    assert len(report["forecasts"]["ridge"]) == report["audit"]["evaluation_events"]


def test_full_phase2_engine_smoke():
    report = HistoricalResearchEngine(seed=8).run_demo(n=64)

    assert report["audit"]["all_forecast_seals_valid"] is True
    assert {"rmc", "ridge", "random_forest", "mlp", "local_level"} <= set(report["metrics"])
    assert len(report["rmc_programs"]) == len(report["outcome_names"])
