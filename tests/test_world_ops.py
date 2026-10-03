from __future__ import annotations

from worldmodel.world_ops import business_summary, forecast_calibration, simulate_world


def test_world_simulation_propagates_signed_relationships() -> None:
    entities = [
        {"id": "a", "name": "Demand", "kind": "metric", "attributes": {"value": 0.0}},
        {"id": "b", "name": "Revenue", "kind": "metric", "attributes": {"value": 0.0}},
    ]
    relations = [
        {
            "source_id": "a",
            "target_id": "b",
            "weight": 1.0,
            "confidence": 1.0,
        }
    ]
    result = simulate_world(
        entities=entities,
        relations=relations,
        shocks={"Demand": 2.0},
        runs=300,
        steps=2,
        noise=0.0,
        seed=7,
    )

    by_name = {row["name"]: row for row in result["outcomes"]}
    assert by_name["Demand"]["mean_change"] == 2.0
    assert by_name["Revenue"]["mean_change"] == 2.0
    assert result["engine"] == "weighted_graph_monte_carlo_v1"


def test_forecast_calibration_and_business_summary() -> None:
    calibration = forecast_calibration(
        [
            {"status": "resolved", "probability": 0.8, "outcome": 1, "brier_score": 0.04},
            {"status": "resolved", "probability": 0.2, "outcome": 0, "brier_score": 0.04},
            {"status": "open", "probability": 0.7},
        ]
    )
    assert calibration["resolved"] == 2
    assert calibration["mean_brier_score"] == 0.04
    assert calibration["accuracy_at_50"] == 1.0

    business = business_summary(
        [
            {"metric": "Revenue", "value": 100.0, "observed_at": "2026-01-01", "unit": "EUR"},
            {"metric": "Revenue", "value": 120.0, "observed_at": "2026-02-01", "unit": "EUR"},
        ]
    )
    assert business["metrics"][0]["latest"] == 120.0
    assert business["metrics"][0]["pct_change"] == 0.2
