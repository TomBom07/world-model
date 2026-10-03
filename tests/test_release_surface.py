from fastapi.testclient import TestClient

import worldmodel
from worldmodel.api import app


def test_package_version_matches_rook_08_release():
    assert worldmodel.__version__ == "0.8.0"


def test_health_and_research_endpoints_are_exposed():
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["version"] == "0.8.0"

    breakthrough = client.get("/api/breakthrough?seed=7")
    assert breakthrough.status_code == 200
    assert breakthrough.json()["all_checks_pass"] is True

    frontier = client.get("/api/frontier?seed=7")
    assert frontier.status_code == 200
    assert frontier.json()["all_checks_pass"] is True


def test_custom_world_endpoint_is_in_release_surface():
    paths = set(app.openapi()["paths"])
    assert "/api/custom/analyze" in paths


def test_local_ai_endpoints_are_in_release_surface():
    paths = set(app.openapi()["paths"])
    assert "/api/ai/status" in paths
    assert "/api/ai/chat" in paths


def test_world_os_release_surface_is_exposed():
    paths = set(app.openapi()["paths"])
    assert "/worlds" in paths
    assert "/api/worlds" in paths
    assert "/api/worlds/{project_id}" in paths
    assert "/api/worlds/{project_id}/simulate" in paths
    assert "/api/worlds/{project_id}/reports" in paths
    assert "/api/worlds/{project_id}/ai/build" in paths
    assert "/api/worlds/{project_id}/paper/trades" in paths
