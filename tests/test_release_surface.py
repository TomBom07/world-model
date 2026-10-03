from fastapi.testclient import TestClient

import worldmodel
from worldmodel.api import app


def test_package_version_matches_v4_release():
    assert worldmodel.__version__ == "0.5.0"


def test_health_and_research_endpoints_are_exposed():
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["version"] == "0.5.0"

    breakthrough = client.get("/api/breakthrough?seed=7")
    assert breakthrough.status_code == 200
    assert breakthrough.json()["all_checks_pass"] is True

    frontier = client.get("/api/frontier?seed=7")
    assert frontier.status_code == 200
    assert frontier.json()["all_checks_pass"] is True
