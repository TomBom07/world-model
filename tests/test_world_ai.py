from __future__ import annotations

from worldmodel.world_ai import extract_json_object, normalize_world_plan


def test_extract_json_object_accepts_fenced_json() -> None:
    result = extract_json_object(
        """Here is the plan:
```json
{"entities":[{"name":"A"}],"relations":[],"claims":[],"forecasts":[]}
```
"""
    )
    assert result["entities"][0]["name"] == "A"


def test_normalize_world_plan_caps_and_sanitizes_values() -> None:
    plan = {
        "entities": [
            {"name": "Demand", "kind": "metric", "value": 1},
            {"name": "Revenue", "kind": "metric", "value": 2},
            {"name": "Demand", "kind": "duplicate", "value": 3},
        ],
        "relations": [
            {
                "source": "Demand",
                "target": "Revenue",
                "relation": "increases",
                "weight": 99,
                "confidence": 2,
            }
        ],
        "claims": [{"text": "Demand drives revenue", "confidence": 0.8}],
        "forecasts": [
            {
                "question": "Will demand rise?",
                "probability": 1.4,
                "horizon": "quarter",
                "rationale": "test",
            }
        ],
        "_model": "local:test",
    }

    normalized = normalize_world_plan(plan)

    assert len(normalized["entities"]) == 2
    assert normalized["relations"][0]["weight"] == 5.0
    assert normalized["relations"][0]["confidence"] == 1.0
    assert normalized["forecasts"][0]["probability"] == 1.0
    assert normalized["model"] == "local:test"
