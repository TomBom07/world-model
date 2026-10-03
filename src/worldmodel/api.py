from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .breakthrough_engine import BreakthroughResearchEngine
from .engine import ResearchEngine
from .historical_engine import HistoricalResearchEngine
from .physics_engine import PhysicsDiscoveryEngine
from .frontier_engine import FrontierResearchEngine
from .strategic_engine import StrategicResearchEngine
from .strategic import ASSETS, EVENTS, MECHANISMS, StrategicMarketSimulator
from .custom_world import analyze_custom_world
from .ollama_client import OllamaUnavailable, chat as ollama_chat, status as ollama_status
from .world_api import router as world_router


app = FastAPI(
    title="WorldModel RMC Lab",
    version="0.7.0",
    description="Reflexive Mechanism Compilation, active identification, theory invention and sealed falsification.",
)

STATIC_DIR = Path(__file__).with_name("static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(world_router)


class CustomWorldRequest(BaseModel):
    columns: list[str] = Field(min_length=2, max_length=64)
    rows: list[list[object]] = Field(min_length=1, max_length=20_000)
    target: str
    features: list[str] = Field(min_length=1, max_length=8)
    holdout_fraction: float = Field(default=0.20, ge=0.15, le=0.40)
    seed: int = Field(default=7, ge=0, le=1_000_000)


class AIMessage(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=12_000)


class AIChatRequest(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    context: str = Field(default="market", max_length=32)
    messages: list[AIMessage] = Field(default_factory=list, max_length=20)
    engine_hint: str | None = Field(default=None, max_length=20_000)
    extra_evidence: dict[str, Any] | None = None
    custom_world: dict[str, Any] | None = None
    seed: int = Field(default=7, ge=0, le=1_000_000)
    target: str = Field(default="growth_equity", max_length=64)


@lru_cache(maxsize=32)
def _cached_demo(seed: int, observations: int, target: str):
    return ResearchEngine(seed=seed).run_demo(n=observations, target=target)


@lru_cache(maxsize=32)
def _cached_strategic(seed: int, observations: int):
    return StrategicResearchEngine(seed=seed).run_demo(n=observations)


@lru_cache(maxsize=32)
def _cached_sealed(seed: int, observations: int):
    return HistoricalResearchEngine(seed=seed).run_demo(n=observations)


@lru_cache(maxsize=32)
def _cached_physics(seed: int, observations: int):
    return PhysicsDiscoveryEngine(seed=seed).run_demo(n=observations)


@lru_cache(maxsize=16)
def _cached_frontier(seed: int):
    return FrontierResearchEngine(seed=seed).run()


@lru_cache(maxsize=16)
def _cached_breakthrough(seed: int):
    return BreakthroughResearchEngine(seed=seed).run()


@lru_cache(maxsize=128)
def _cached_scenario(seed: int, observations: int, event_kind: str, magnitude: float):
    """Counterfactual reaction fingerprint for a naturally occurring market event.

    This does not trade or intervene in a real market. It asks how each synthetic
    candidate world would react if the specified event were observed.
    """
    simulator = StrategicMarketSimulator(seed=seed)
    events = simulator.generate_events(observations)
    prefix = min(120, observations // 2)
    event_index = min(
        observations - 20,
        max(prefix + 12, int(observations * 0.62)),
    )

    predictions: dict[str, dict[str, float]] = {}
    vectors: dict[str, np.ndarray] = {}
    for mechanism in MECHANISMS:
        vector = simulator.counterfactual_fingerprint(
            mechanism,
            events=events,
            event_index=event_index,
            event_kind=event_kind,
            magnitude=magnitude,
            horizon=3,
        )
        vectors[mechanism] = vector
        predictions[mechanism] = {
            asset: float(value)
            for asset, value in zip(ASSETS, vector, strict=True)
        }

    first, second = MECHANISMS
    difference = np.abs(vectors[first] - vectors[second])
    diagnostic_index = int(np.argmax(difference))
    information_score = float(
        np.linalg.norm(vectors[first] - vectors[second]) / 0.08
    )

    return {
        "seed": seed,
        "observations": observations,
        "event_index": event_index,
        "event": {
            "kind": event_kind,
            "magnitude": magnitude,
            "label": f"{event_kind} {magnitude:+.1f}σ",
        },
        "asset_names": list(ASSETS),
        "mechanisms": list(MECHANISMS),
        "predictions": predictions,
        "absolute_disagreement": {
            asset: float(value)
            for asset, value in zip(ASSETS, difference, strict=True)
        },
        "most_diagnostic_asset": ASSETS[diagnostic_index],
        "information_score": information_score,
        "scientific_boundary": (
            "This is a counterfactual inside the controlled synthetic market. "
            "It is an identification aid, not a forecast of real asset returns "
            "and not a trading signal."
        ),
    }




def _ai_evidence(
    context: str,
    *,
    seed: int,
    target: str,
    custom_world: dict[str, Any] | None = None,
    extra_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if context == "market":
        data = _cached_strategic(seed, 260)
        evidence: dict[str, Any] = {
            "world_kind": "controlled_synthetic_market",
            "active_identification": data.get("active_identification"),
            "observational_equivalence": data.get("observational_equivalence"),
            "identification_benchmark": data.get("identification_benchmark"),
            "belief_ablation": data.get("belief_ablation"),
            "hidden_mechanics": data.get("hidden_mechanics"),
            "scientific_boundary": data.get("scientific_boundary"),
        }
    elif context == "physics":
        data = _cached_physics(seed, 240)
        evidence = {
            "world_kind": "controlled_synthetic_physics",
            "active_identification": data.get("active_identification"),
            "passive_equivalence": data.get("passive_equivalence"),
            "identification_benchmark": data.get("identification_benchmark"),
            "mechanisms": data.get("mechanisms"),
            "preregistration": data.get("preregistration"),
            "scientific_boundary": data.get("scientific_boundary"),
        }
    elif context == "discovery":
        data = _cached_frontier(seed)
        evidence = {
            "world_kind": "controlled_frontier_discovery_suite",
            "checks": data.get("checks"),
            "cross_domain_summary": data.get("cross_domain_summary"),
            "natural_experiments": data.get("natural_experiments"),
            "latent_laws": data.get("latent_laws"),
            "theory_invention": data.get("theory_invention"),
            "ontology_evolution": data.get("ontology_evolution"),
            "unified_objective": data.get("unified_objective"),
            "prospective_falsification": data.get("prospective_falsification"),
            "scientific_boundary": data.get("scientific_boundary"),
        }
    elif context == "validation":
        data = _cached_sealed(seed, 120)
        evidence = {
            "world_kind": "sealed_historical_shaped_replay",
            "audit": data.get("audit"),
            "metrics": data.get("metrics"),
            "manifest": data.get("manifest"),
            "scientific_boundary": data.get("scientific_boundary"),
        }
    elif context == "custom":
        evidence = {
            "world_kind": "user_uploaded_observational_table",
            "analysis": custom_world or {
                "status": "no custom analysis is available yet",
            },
        }
    else:
        data = _cached_demo(seed, 360, target)
        evidence = {
            "world_kind": "symbolic_compiler_demo",
            "analysis": data,
        }

    if extra_evidence:
        evidence["extra_evidence"] = extra_evidence
    return evidence

@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/worlds")
def worlds_workspace() -> FileResponse:
    return FileResponse(STATIC_DIR / "worlds.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "rmc-v4", "version": "0.7.0"}


@app.get("/api/demo")
def demo(
    seed: int = Query(7, ge=0, le=1_000_000),
    observations: int = Query(360, ge=120, le=1000),
    target: str = Query("growth_equity"),
):
    allowed = {"growth_equity", "value_equity", "two_year_yield", "usd", "gold", "volatility"}
    if target not in allowed:
        target = "growth_equity"
    return _cached_demo(seed, observations, target)


@app.get("/api/strategic")
def strategic(
    seed: int = Query(7, ge=0, le=1_000_000),
    observations: int = Query(260, ge=180, le=600),
):
    return _cached_strategic(seed, observations)


@app.get("/api/sealed")
def sealed(
    seed: int = Query(7, ge=0, le=1_000_000),
    observations: int = Query(120, ge=64, le=500),
):
    return _cached_sealed(seed, observations)


@app.get("/api/physics")
def physics(
    seed: int = Query(7, ge=0, le=1_000_000),
    observations: int = Query(240, ge=180, le=600),
):
    return _cached_physics(seed, observations)


@app.get("/api/frontier")
def frontier(seed: int = Query(7, ge=0, le=1_000_000)):
    return _cached_frontier(seed)


@app.get("/api/breakthrough")
def breakthrough(seed: int = Query(7, ge=0, le=1_000_000)):
    return _cached_breakthrough(seed)


@app.get("/api/scenario")
def scenario(
    seed: int = Query(7, ge=0, le=1_000_000),
    observations: int = Query(260, ge=180, le=600),
    event_kind: str = Query("liquidity"),
    magnitude: float = Query(-2.0, ge=-4.0, le=4.0),
):
    if event_kind not in EVENTS:
        event_kind = "liquidity"
    return _cached_scenario(seed, observations, event_kind, round(float(magnitude), 3))




@app.get("/api/ai/status")
def ai_status():
    return ollama_status()


@app.post("/api/ai/chat")
def ai_chat(payload: AIChatRequest):
    evidence = _ai_evidence(
        payload.context,
        seed=payload.seed,
        target=payload.target,
        custom_world=payload.custom_world,
        extra_evidence=payload.extra_evidence,
    )
    try:
        return ollama_chat(
            model=payload.model,
            context=payload.context,
            evidence=evidence,
            messages=[
                {"role": message.role, "content": message.content}
                for message in payload.messages
            ],
            engine_hint=payload.engine_hint,
        )
    except OllamaUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

@app.post("/api/custom/analyze")
def custom_analyze(payload: CustomWorldRequest):
    try:
        return analyze_custom_world(
            columns=payload.columns,
            rows=payload.rows,
            target=payload.target,
            features=payload.features,
            holdout_fraction=payload.holdout_fraction,
            seed=payload.seed,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
