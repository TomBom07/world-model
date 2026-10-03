from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .breakthrough_engine import BreakthroughResearchEngine
from .engine import ResearchEngine
from .historical_engine import HistoricalResearchEngine
from .physics_engine import PhysicsDiscoveryEngine
from .frontier_engine import FrontierResearchEngine
from .strategic_engine import StrategicResearchEngine


app = FastAPI(
    title="WorldModel RMC Lab",
    version="0.5.0",
    description="Reflexive Mechanism Compilation, active identification, theory invention and sealed falsification.",
)

STATIC_DIR = Path(__file__).with_name("static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "rmc-v4", "version": "0.5.0"}


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
