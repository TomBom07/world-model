from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .ollama_client import OllamaUnavailable, chat as ollama_chat
from .world_ops import (
    build_living_report,
    business_summary,
    forecast_calibration,
    simulate_world,
    world_health,
)
from .world_store import WorldStore


router = APIRouter(prefix="/api/worlds", tags=["worlds"])


def _store() -> WorldStore:
    return WorldStore()


def _not_found(error: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail=f"World object not found: {error.args[0]}")


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(default="research", max_length=40)
    goal: str = Field(default="", max_length=2000)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    goal: str | None = Field(default=None, max_length=2000)
    settings: dict[str, Any] | None = None


class EntityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: str = Field(default="concept", max_length=60)
    attributes: dict[str, Any] = Field(default_factory=dict)


class RelationCreate(BaseModel):
    source_id: str
    target_id: str
    relation: str = Field(min_length=1, max_length=160)
    weight: float = Field(default=0.0, ge=-5.0, le=5.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: list[Any] = Field(default_factory=list, max_length=100)


class ClaimCreate(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    status: str = Field(default="hypothesis", max_length=40)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: list[Any] = Field(default_factory=list, max_length=100)


class SourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    url: str | None = Field(default=None, max_length=2000)
    source_type: str = Field(default="note", max_length=60)
    excerpt: str = Field(default="", max_length=20_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ForecastCreate(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    probability: float = Field(ge=0.0, le=1.0)
    horizon: str = Field(default="", max_length=160)
    resolves_at: str | None = Field(default=None, max_length=80)
    rationale: str = Field(default="", max_length=10_000)
    evidence_cutoff: str | None = Field(default=None, max_length=80)


class ForecastResolve(BaseModel):
    outcome: bool


class SimulationCreate(BaseModel):
    name: str = Field(default="Scenario", min_length=1, max_length=160)
    shocks: dict[str, float] = Field(default_factory=dict)
    runs: int = Field(default=2000, ge=100, le=20_000)
    steps: int = Field(default=4, ge=1, le=12)
    noise: float = Field(default=0.04, ge=0.0, le=0.5)
    seed: int = Field(default=7, ge=0, le=1_000_000)


class ObservationCreate(BaseModel):
    metric: str = Field(min_length=1, max_length=160)
    value: float
    observed_at: str = Field(min_length=1, max_length=80)
    unit: str = Field(default="", max_length=40)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaperAccountCreate(BaseModel):
    initial_cash: float = Field(default=100_000.0, gt=0.0, le=1_000_000_000.0)


class PaperTradeCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    side: str = Field(default="buy", max_length=8)
    quantity: float = Field(gt=0.0, le=1_000_000_000.0)
    entry_price: float = Field(gt=0.0, le=1_000_000_000.0)
    thesis: str = Field(default="", max_length=5000)
    falsifier: str = Field(default="", max_length=5000)


class PaperTradeClose(BaseModel):
    exit_price: float = Field(gt=0.0, le=1_000_000_000.0)


class ReportGenerate(BaseModel):
    title: str = Field(default="Living World Report", min_length=1, max_length=200)
    ollama_model: str | None = Field(default=None, max_length=200)


@router.get("")
def list_worlds():
    return {"projects": _store().list_projects()}


@router.post("")
def create_world(payload: ProjectCreate):
    return _store().create_project(name=payload.name, kind=payload.kind, goal=payload.goal)


@router.get("/{project_id}")
def get_world(project_id: str):
    try:
        snapshot = _store().snapshot(project_id)
    except KeyError as error:
        raise _not_found(error) from error
    snapshot["health"] = world_health(snapshot)
    snapshot["business"] = business_summary(snapshot["observations"])
    snapshot["forecast_calibration"] = forecast_calibration(snapshot["forecasts"])
    return snapshot


@router.patch("/{project_id}")
def update_world(project_id: str, payload: ProjectUpdate):
    try:
        return _store().update_project(
            project_id,
            name=payload.name,
            goal=payload.goal,
            settings=payload.settings,
        )
    except KeyError as error:
        raise _not_found(error) from error


@router.delete("/{project_id}")
def delete_world(project_id: str):
    try:
        _store().delete_project(project_id)
    except KeyError as error:
        raise _not_found(error) from error
    return {"deleted": True, "project_id": project_id}


@router.post("/{project_id}/entities")
def create_entity(project_id: str, payload: EntityCreate):
    try:
        return _store().add_entity(
            project_id,
            name=payload.name,
            kind=payload.kind,
            attributes=payload.attributes,
        )
    except KeyError as error:
        raise _not_found(error) from error


@router.post("/{project_id}/relations")
def create_relation(project_id: str, payload: RelationCreate):
    try:
        return _store().add_relation(
            project_id,
            source_id=payload.source_id,
            target_id=payload.target_id,
            relation=payload.relation,
            weight=payload.weight,
            confidence=payload.confidence,
            evidence=payload.evidence,
        )
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/{project_id}/claims")
def create_claim(project_id: str, payload: ClaimCreate):
    try:
        return _store().add_claim(
            project_id,
            text=payload.text,
            status=payload.status,
            confidence=payload.confidence,
            evidence=payload.evidence,
        )
    except KeyError as error:
        raise _not_found(error) from error


@router.post("/{project_id}/sources")
def create_source(project_id: str, payload: SourceCreate):
    try:
        return _store().add_source(
            project_id,
            title=payload.title,
            url=payload.url,
            source_type=payload.source_type,
            excerpt=payload.excerpt,
            metadata=payload.metadata,
        )
    except KeyError as error:
        raise _not_found(error) from error


@router.post("/{project_id}/forecasts")
def create_forecast(project_id: str, payload: ForecastCreate):
    try:
        return _store().add_forecast(
            project_id,
            question=payload.question,
            probability=payload.probability,
            horizon=payload.horizon,
            resolves_at=payload.resolves_at,
            rationale=payload.rationale,
            evidence_cutoff=payload.evidence_cutoff,
        )
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/{project_id}/forecasts/{forecast_id}/resolve")
def resolve_forecast(project_id: str, forecast_id: str, payload: ForecastResolve):
    try:
        forecast = _store().get_forecast(forecast_id)
        if forecast["project_id"] != project_id:
            raise KeyError(forecast_id)
        return _store().resolve_forecast(forecast_id, outcome=payload.outcome)
    except KeyError as error:
        raise _not_found(error) from error


@router.post("/{project_id}/simulate")
def run_simulation(project_id: str, payload: SimulationCreate):
    store = _store()
    try:
        snapshot = store.snapshot(project_id)
    except KeyError as error:
        raise _not_found(error) from error

    try:
        result = simulate_world(
            entities=snapshot["entities"],
            relations=snapshot["relations"],
            shocks=payload.shocks,
            runs=payload.runs,
            steps=payload.steps,
            noise=payload.noise,
            seed=payload.seed,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return store.add_simulation(
        project_id,
        name=payload.name,
        config=payload.model_dump(),
        result=result,
    )


@router.post("/{project_id}/observations")
def create_observation(project_id: str, payload: ObservationCreate):
    try:
        return _store().add_observation(
            project_id,
            metric=payload.metric,
            value=payload.value,
            observed_at=payload.observed_at,
            unit=payload.unit,
            metadata=payload.metadata,
        )
    except KeyError as error:
        raise _not_found(error) from error


@router.get("/{project_id}/business")
def get_business(project_id: str):
    try:
        observations = _store().list_observations(project_id)
    except KeyError as error:
        raise _not_found(error) from error
    return business_summary(observations)


@router.post("/{project_id}/paper")
def create_paper_account(project_id: str, payload: PaperAccountCreate):
    try:
        return _store().ensure_paper_account(project_id, initial_cash=payload.initial_cash)
    except KeyError as error:
        raise _not_found(error) from error


@router.get("/{project_id}/paper")
def get_paper_account(project_id: str):
    try:
        return _store().paper_snapshot(project_id)
    except KeyError as error:
        raise _not_found(error) from error


@router.post("/{project_id}/paper/trades")
def create_paper_trade(project_id: str, payload: PaperTradeCreate):
    try:
        return _store().add_paper_trade(
            project_id,
            symbol=payload.symbol,
            side=payload.side,
            quantity=payload.quantity,
            entry_price=payload.entry_price,
            thesis=payload.thesis,
            falsifier=payload.falsifier,
        )
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/{project_id}/paper/trades/{trade_id}/close")
def close_paper_trade(project_id: str, trade_id: str, payload: PaperTradeClose):
    try:
        trade = _store().get_paper_trade(trade_id)
        if trade["project_id"] != project_id:
            raise KeyError(trade_id)
        return _store().close_paper_trade(trade_id, exit_price=payload.exit_price)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/{project_id}/reports")
def generate_report(project_id: str, payload: ReportGenerate):
    store = _store()
    try:
        snapshot = store.snapshot(project_id)
    except KeyError as error:
        raise _not_found(error) from error

    content = build_living_report(snapshot)

    if payload.ollama_model:
        try:
            response = ollama_chat(
                model=payload.ollama_model,
                context="project_report",
                evidence=content,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Write a deep but concise living intelligence report from this structured world state. "
                            "Use sections: Executive assessment, Current world, Competing hypotheses, Forecasts, "
                            "Scenario implications, Key uncertainties, What would change the view, and Next actions. "
                            "Do not invent evidence or causal certainty."
                        ),
                    }
                ],
                engine_hint=content["executive_summary"],
            )
            content["narrative"] = response["content"]
            content["narrative_model"] = response["model"]
        except OllamaUnavailable as error:
            content["narrative_error"] = str(error)

    return store.add_report(project_id, title=payload.title, content=content)
