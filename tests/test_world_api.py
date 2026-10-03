from __future__ import annotations

from fastapi.testclient import TestClient

from worldmodel.api import app


def test_world_os_api_end_to_end(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ROOK_DB_PATH", str(tmp_path / "api.db"))
    client = TestClient(app)

    created = client.post(
        "/api/worlds",
        json={"name": "Test world", "kind": "research", "goal": "Understand a system"},
    )
    assert created.status_code == 200
    project = created.json()
    project_id = project["id"]

    first = client.post(
        f"/api/worlds/{project_id}/entities",
        json={"name": "Demand", "kind": "metric", "attributes": {"value": 0}},
    ).json()
    second = client.post(
        f"/api/worlds/{project_id}/entities",
        json={"name": "Revenue", "kind": "metric", "attributes": {"value": 0}},
    ).json()

    relation = client.post(
        f"/api/worlds/{project_id}/relations",
        json={
            "source_id": first["id"],
            "target_id": second["id"],
            "relation": "increases",
            "weight": 0.8,
            "confidence": 0.9,
        },
    )
    assert relation.status_code == 200

    forecast = client.post(
        f"/api/worlds/{project_id}/forecasts",
        json={"question": "Will demand rise?", "probability": 0.65, "horizon": "quarter"},
    )
    assert forecast.status_code == 200
    forecast_id = forecast.json()["id"]

    resolved = client.post(
        f"/api/worlds/{project_id}/forecasts/{forecast_id}/resolve",
        json={"outcome": True},
    )
    assert resolved.status_code == 200
    assert resolved.json()["brier_score"] > 0

    simulation = client.post(
        f"/api/worlds/{project_id}/simulate",
        json={"name": "Demand shock", "shocks": {first["id"]: 1.5}, "runs": 200, "steps": 2, "noise": 0},
    )
    assert simulation.status_code == 200
    assert simulation.json()["result"]["outcomes"]

    report = client.post(
        f"/api/worlds/{project_id}/reports",
        json={"title": "Test report"},
    )
    assert report.status_code == 200
    assert "executive_summary" in report.json()["content"]

    snapshot = client.get(f"/api/worlds/{project_id}")
    assert snapshot.status_code == 200
    payload = snapshot.json()
    assert payload["health"]["entities"] == 2
    assert payload["forecast_calibration"]["resolved"] == 1


def test_world_workspace_route_exists() -> None:
    client = TestClient(app)
    response = client.get("/worlds")
    assert response.status_code == 200
    assert "Rook Worlds" in response.text
