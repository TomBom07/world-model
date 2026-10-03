from fastapi.testclient import TestClient

import worldmodel
from worldmodel.api import app
from worldmodel.frontier_engine import FrontierResearchEngine


def test_integrated_version_and_health():
    assert worldmodel.__version__ == "0.5.0"
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "engine": "openmechanism-v4",
        "version": "0.5.0",
    }


def test_frontier_default_seed_passes():
    report = FrontierResearchEngine(seed=7).run()
    print("V4_CHECKS", report["checks"])
    assert report["all_checks_pass"], report


def test_frontier_api_is_exposed():
    client = TestClient(app)
    response = client.get("/api/frontier?seed=7")
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "v4-frontier-suite"
    assert payload["all_checks_pass"] is True
