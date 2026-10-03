from __future__ import annotations

from worldmodel.world_store import WorldStore


def test_world_store_persists_epistemic_world_and_scores_forecasts(tmp_path) -> None:
    store = WorldStore(tmp_path / "rook.db")
    project = store.create_project(
        name="AI infrastructure",
        kind="research",
        goal="Understand power, compute and demand constraints.",
    )

    power = store.add_entity(project["id"], name="Power availability", kind="metric", attributes={"value": 1.0})
    demand = store.add_entity(project["id"], name="Compute demand", kind="metric", attributes={"value": 2.0})
    relation = store.add_relation(
        project["id"],
        source_id=power["id"],
        target_id=demand["id"],
        relation="constrains",
        weight=-0.6,
        confidence=0.8,
    )
    claim = store.add_claim(
        project["id"],
        text="Power becomes the binding constraint.",
        confidence=0.65,
    )
    forecast = store.add_forecast(
        project["id"],
        question="Will grid connection delays rise before 2028?",
        probability=0.7,
        horizon="2 years",
    )
    resolved = store.resolve_forecast(forecast["id"], outcome=True)

    snapshot = store.snapshot(project["id"])
    assert relation["relation"] == "constrains"
    assert claim["status"] == "hypothesis"
    assert resolved["status"] == "resolved"
    assert abs(resolved["brier_score"] - 0.09) < 1e-9
    assert len(snapshot["entities"]) == 2
    assert snapshot["forecasts"][0]["outcome"] == 1


def test_paper_trade_guardrails_limit_single_trade_and_gross_exposure(tmp_path) -> None:
    store = WorldStore(tmp_path / "rook.db")
    project = store.create_project(name="Portfolio", kind="markets")
    store.ensure_paper_account(project["id"], initial_cash=100_000)

    trade = store.add_paper_trade(
        project["id"],
        symbol="NVDA",
        side="buy",
        quantity=100,
        entry_price=200,
        thesis="Paper thesis",
        falsifier="Falsifier",
    )
    assert trade["status"] == "open"

    try:
        store.add_paper_trade(
            project["id"],
            symbol="AMD",
            side="buy",
            quantity=200,
            entry_price=200,
        )
    except ValueError as error:
        assert "25%" in str(error)
    else:
        raise AssertionError("Expected single-trade exposure guardrail")

    closed = store.close_paper_trade(trade["id"], exit_price=220)
    assert closed["status"] == "closed"
    assert closed["realized_pnl"] == 2000
