from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .engine import ResearchEngine
from .strategic_engine import StrategicResearchEngine


app = FastAPI(
    title="WorldModel RMC Lab",
    version="0.2.0",
    description="Reflexive Mechanism Compilation and active hidden-world identification.",
)

STATIC_DIR = Path(__file__).with_name("static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@lru_cache(maxsize=32)
def _cached_demo(seed: int, observations: int, target: str):
    return ResearchEngine(seed=seed).run_demo(n=observations, target=target)


@lru_cache(maxsize=32)
def _cached_strategic(seed: int, observations: int):
    return StrategicResearchEngine(seed=seed).run_demo(n=observations)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "rmc-v1"}


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
