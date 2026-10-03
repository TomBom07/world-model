from __future__ import annotations

from fastapi.testclient import TestClient

from worldmodel.api import app


def test_custom_world_api_analyzes_json_table() -> None:
    rows = [[float(i), float(2 * i + 1)] for i in range(48)]
    response = TestClient(app).post(
        "/api/custom/analyze",
        json={
            "columns": ["x", "y"],
            "rows": rows,
            "target": "y",
            "features": ["x"],
            "holdout_fraction": 0.2,
            "seed": 7,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["dataset"]["target"] == "y"
    assert payload["symbolic_model"]["holdout"]["r2"] > 0.99
