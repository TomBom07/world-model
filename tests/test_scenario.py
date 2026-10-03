from __future__ import annotations

from worldmodel.api import _cached_scenario


def test_counterfactual_scenario_returns_distinct_world_reactions() -> None:
    result = _cached_scenario(
        seed=7,
        observations=260,
        event_kind="liquidity",
        magnitude=-2.0,
    )

    assert result["event"]["kind"] == "liquidity"
    assert result["event"]["magnitude"] == -2.0
    assert result["information_score"] > 0.0
    assert result["most_diagnostic_asset"] in result["asset_names"]

    belief = result["predictions"]["belief_reflexive"]
    liquidity = result["predictions"]["liquidity_reflexive"]

    assert set(belief) == set(result["asset_names"])
    assert set(liquidity) == set(result["asset_names"])
    assert any(abs(belief[name] - liquidity[name]) > 1e-6 for name in result["asset_names"])


def test_scenario_is_deterministic_for_same_inputs() -> None:
    first = _cached_scenario(11, 240, "policy", 1.5)
    second = _cached_scenario(11, 240, "policy", 1.5)

    assert first == second
